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
        result = _execute_with_retries(q.count(q.match(q.index(f"all_{collection}"))))
        print(f"\t{collection}: {result}")


def _load_predictions(data):
    predictions = data["predictions"]
    # Not very efficient, but we create documents one at a time to retrieve each ID
    # and save it for later, because we want to maintain the association between
    # the Django PK and Fauna ID.
    for document in predictions.values():
        ml_model_id = data["ml_models"][document["ml_model_id"]]["id"]
        document["ml_model_id"] = q.ref(q.collection("ml_models"), ml_model_id)

        match_id = data["matches"][document["match_id"]]["id"]
        document["match_id"] = q.ref(q.collection("matches"), match_id)

        predicted_winner_id = data["teams"][document["predicted_winner_id"]]["id"]
        document["predicted_winner_id"] = q.ref(
            q.collection("teams"), predicted_winner_id
        )

        result = _execute_with_retries(
            q.create(q.collection("predictions"), {"data": document})
        )
        document["id"] = result["ref"].id()


def _load_team_matches(data):
    team_matches = data["team_matches"]
    # Not very efficient, but we create documents one at a time to retrieve each ID
    # and save it for later, because we want to maintain the association between
    # the Django PK and Fauna ID.
    for document in team_matches.values():
        team_id = data["teams"][document["team_id"]]["id"]
        document["team_id"] = q.ref(q.collection("teams"), team_id)

        match_id = data["matches"][document["match_id"]]["id"]
        document["match_id"] = q.ref(q.collection("matches"), match_id)

        result = _execute_with_retries(
            q.create(q.collection("team_matches"), {"data": document})
        )
        document["id"] = result["ref"].id()


def _load_matches(data):
    matches = data["matches"]
    # Not very efficient, but we create documents one at a time to retrieve each ID
    # and save it for later, because we want to maintain the association between
    # the Django PK and Fauna ID.
    for document in matches.values():
        if document["winner_id"] is not None:
            winner_id = data["teams"][document["winner_id"]]["id"]
            document["winner_id"] = q.ref(q.collection("teams"), winner_id)

        result = _execute_with_retries(
            q.create(q.collection("matches"), {"data": document})
        )

        document["id"] = result["ref"].id()


def _load_ml_models(ml_models):
    # Not very efficient, but we create documents one at a time to retrieve each ID
    # and save it for later, because we want to maintain the association between
    # the Django PK and Fauna ID.
    for document in ml_models.values():
        result = _execute_with_retries(q.create(q.collection("ml_models"), document))
        document["id"] = result["ref"].id()


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
            q.paginate(q.match(q.index("all_teams"))),
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

    return {**acc, collection: {**acc.get(collection, {}), record["pk"]: document}}


def _read_data_dump(filepath):
    with open(filepath, "r") as f:
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
    if database_url.netloc != "db.fauna.com":
        _set_up_fauna()
    _delete_data()
    subprocess.run("alembic upgrade head", check=True, shell=True)
    data_dump = _read_data_dump(filepath)
    _load_data_into_fauna(data_dump)
    _print_document_counts()


if __name__ == "__main__":
    cli_args = sys.argv
    dump_filepath = cli_args[1]
    main(dump_filepath)
