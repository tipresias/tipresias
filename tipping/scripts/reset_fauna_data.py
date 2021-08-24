"""Script for loading a Django data dump into a Fauna DB."""

import os
import sys
import json
from functools import reduce
import subprocess
from time import sleep
from datetime import datetime
from urllib.parse import urlparse
from dateutil import parser as date_parser

from faunadb.client import FaunaClient
from faunadb import query as q, errors as fauna_errors

MODEL_TO_COLLECTION = {
    "server.team": "teams",
    "server.mlmodel": "ml_models",
    "server.match": "matches",
    "server.teammatch": "team_matches",
    "server.prediction": "predictions",
}

COLLECTIONS = MODEL_TO_COLLECTION.values()
REFERENCES = [
    "predicted_winner",
    "winner",
    "team",
    "match",
    "team_match",
    "prediction",
    "ml_model",
]
REFERENCE_MAP = {ref: ref + "_id" for ref in REFERENCES}
NON_FAUNA_FIELDS = ["created_at", "updated_at"]

FAUNA_SECRET = os.getenv("FAUNA_SECRET", "")
DATABASE_HOST = os.getenv("DATABASE_HOST", "")
FAUNA_SCHEME = os.getenv("FAUNA_SCHEME", "")
database_url = urlparse(f"{FAUNA_SCHEME}://{DATABASE_HOST}")
client = FaunaClient(
    scheme=database_url.scheme,
    domain=database_url.hostname,
    port=database_url.port,
    secret=FAUNA_SECRET,
)


def _execute_with_retries(query, retries=0):
    # Sometimes Fauna needs time to do something when trying to create collections,
    # so we retry with gradual backoff. This seems to only be an issue when
    # creating/deleting collections in quick succession, so might not matter
    # in production where that happens less frequently.
    try:
        return client.query(query)
    except fauna_errors.BadRequest as err:
        if "document data is not valid" not in str(err) or retries >= 5:
            raise err

        sleep(retries)
        return _execute_with_retries(query, retries=(retries + 1))


def _print_document_counts():
    print("\nDocument counts by collection")
    for collection in COLLECTIONS:
        result = _execute_with_retries(q.count(q.match(q.index(f"{collection}_all"))))
        print(f"\t{collection}: {result}")


def _assign_ref(ref_collection, ref_map, record_id):
    return q.if_(
        q.is_null(record_id),
        None,
        q.ref(ref_collection, q.select([q.to_string(record_id), "id"], ref_map)),
    )


def _create_documents(let_params, records, build_document):
    return _execute_with_retries(
        q.let(
            let_params,
            q.map_(
                q.lambda_(
                    "document",
                    q.create(
                        q.var("collection"),
                        {"data": build_document(q.var("document"))},
                    ),
                ),
                records,
            ),
        )
    )


def _load_predictions(data):
    predictions = data["predictions"]
    records = list(predictions.values())

    build_document = lambda prediction: q.to_object(
        q.map_(
            q.lambda_(
                ["key", "value"],
                [
                    q.var("key"),
                    q.if_(
                        q.equals(q.var("key"), "predicted_winner_id"),
                        _assign_ref(q.var("teams"), q.var("team_map"), q.var("value")),
                        q.if_(
                            q.equals(q.var("key"), "match_id"),
                            _assign_ref(
                                q.var("matches"), q.var("match_map"), q.var("value")
                            ),
                            q.if_(
                                q.equals(q.var("key"), "ml_model_id"),
                                _assign_ref(
                                    q.var("ml_models"),
                                    q.var("ml_model_map"),
                                    q.var("value"),
                                ),
                                q.var("value"),
                            ),
                        ),
                    ),
                ],
            ),
            q.to_array(prediction),
        )
    )
    let_params = {
        "collection": q.collection("predictions"),
        "teams": q.collection("teams"),
        "team_map": data["teams"],
        "matches": q.collection("matches"),
        "match_map": data["matches"],
        "ml_models": q.collection("ml_models"),
        "ml_model_map": data["ml_models"],
    }

    documents = _create_documents(let_params, records, build_document)

    for record, document in zip(records, documents):
        record["id"] = document["ref"].id()


def _load_team_matches(data):
    team_matches = data["team_matches"]
    records = list(team_matches.values())
    build_document = lambda team_match: q.to_object(
        q.map_(
            q.lambda_(
                ["key", "value"],
                [
                    q.var("key"),
                    q.if_(
                        q.equals(q.var("key"), "team_id"),
                        _assign_ref(q.var("teams"), q.var("team_map"), q.var("value")),
                        q.if_(
                            q.equals(q.var("key"), "match_id"),
                            _assign_ref(
                                q.var("matches"),
                                q.var("match_map"),
                                q.var("value"),
                            ),
                            q.var("value"),
                        ),
                    ),
                ],
            ),
            q.to_array(team_match),
        )
    )
    let_params = {
        "collection": q.collection("team_matches"),
        "teams": q.collection("teams"),
        "team_map": data["teams"],
        "matches": q.collection("matches"),
        "match_map": data["matches"],
    }

    documents = _create_documents(let_params, records, build_document)

    for record, document in zip(records, documents):
        record["id"] = document["ref"].id()


def _load_matches(data):
    matches = data["matches"]
    records = list(matches.values())
    build_document = lambda match: q.to_object(
        q.map_(
            q.lambda_(
                ["key", "value"],
                [
                    q.var("key"),
                    q.if_(
                        q.equals(q.var("key"), "winner_id"),
                        _assign_ref(q.var("teams"), q.var("team_map"), q.var("value")),
                        q.var("value"),
                    ),
                ],
            ),
            q.to_array(match),
        )
    )
    let_params = {
        "collection": q.collection("matches"),
        "teams": q.collection("teams"),
        "team_map": data["teams"],
    }

    documents = _create_documents(let_params, records, build_document)

    for record, document in zip(records, documents):
        record["id"] = document["ref"].id()


def _load_ml_models(ml_models):
    records = list(ml_models.values())

    build_document = lambda ml_model: ml_model
    let_params = {"collection": q.collection("ml_models")}
    documents = _create_documents(let_params, records, build_document)

    for record, document in zip(records, documents):
        record["id"] = document["ref"].id()


def _load_data_into_fauna(data):
    print("Loading ml_models...")
    _load_ml_models(data["ml_models"])
    print("Loading matches...")
    _load_matches(data)
    print("Loading team_matches...")
    _load_team_matches(data)
    print("Loading predictions...")
    _load_predictions(data)


def _convert_value(value):
    try:
        return date_parser.parse(value)
    except (date_parser.ParserError, TypeError):
        return value


def _convert_to_document(record):
    is_fauna_field = lambda key: key not in NON_FAUNA_FIELDS
    convert_key = lambda key: REFERENCE_MAP.get(key, key)
    document = {
        convert_key(key): _convert_value(value)
        for key, value in record["fields"].items()
        if is_fauna_field(key)
    }
    return document


def _assign_ids_to_teams(teams):
    result = _execute_with_retries(
        q.map_(
            q.lambda_("team", q.get(q.var("team"))),
            q.paginate(q.match(q.index("teams_all"))),
        )
    )
    team_documents = result["data"]

    for team in teams.values():
        team_document = next(
            doc for doc in team_documents if doc["data"]["name"] == team["name"]
        )
        team["id"] = team_document["ref"].id()


def _collect_db_data(acc, record):
    collection = MODEL_TO_COLLECTION[record["model"]]
    document = _convert_to_document(record)

    return {**acc, collection: {**acc.get(collection, {}), str(record["pk"]): document}}


def _read_data_dump(filepath):
    with open(filepath, "r", encoding="utf-8") as f:
        data_dump = json.load(f)

    db_data = reduce(_collect_db_data, data_dump, {})
    _assign_ids_to_teams(db_data["teams"])

    return db_data


def _delete_data():
    resources = [q.functions(), q.indexes(), q.collections()]
    delete = lambda res: q.foreach(
        q.lambda_("res", q.delete(q.var("res"))), q.paginate(res)
    )
    delete_queries = [delete(res) for res in resources]

    _execute_with_retries(q.do(*delete_queries))


def _set_up_fauna():
    # We need to create the local endpoint every time, because it gets lost
    # with each new Docker container.
    subprocess.run(
        f"npx fauna add-endpoint {FAUNA_SCHEME}://{DATABASE_HOST}/ --alias localhost --key secret",
        check=True,
        shell=True,
    )


def main(filepath):
    """Load a Django data dump into a Fauna DB."""
    start_time = datetime.now()
    print("\nStart time:", start_time, "\n")

    if database_url.netloc != "db.fauna.com":
        _set_up_fauna()

    _delete_data()
    subprocess.run("alembic upgrade head", check=True, shell=True)
    data_dump = _read_data_dump(filepath)
    _load_data_into_fauna(data_dump)

    end_time = datetime.now()
    print("\nEnd time:", end_time, "\n")
    print("\nTotal run time:", end_time - start_time, "\n")
    _print_document_counts()


if __name__ == "__main__":
    cli_args = sys.argv
    dump_filepath = cli_args[1]
    main(dump_filepath)
