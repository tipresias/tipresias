"""Translate a INSERT SQL query into an equivalent FQL query."""

import typing
from datetime import datetime

from sqlparse import sql as token_groups
from sqlparse import tokens as token_types
from faunadb import query as q
from faunadb.objects import _Expr as QueryExpression

from sqlalchemy_fauna import exceptions
from . import common, models


def _build_document(
    table: models.Table,
    value_group: token_groups.Values,
) -> typing.Dict[str, typing.Union[str, int, float, datetime, None, bool]]:
    val_idx, parenthesis_group = value_group.token_next_by(i=token_groups.Parenthesis)
    value_identifiers = parenthesis_group.flatten()

    _, additional_parenthesis_group = value_group.token_next_by(
        i=token_groups.Parenthesis, idx=val_idx
    )
    if additional_parenthesis_group is not None:
        raise exceptions.NotSupportedError(
            "INSERT for multiple rows is not supported yet."
        )

    values = [
        value
        for value in value_identifiers
        if not value.ttype == token_types.Punctuation and not value.is_whitespace
    ]
    column_names = list(map(str, table.columns))

    assert len(column_names) == len(
        values
    ), f"Lengths didn't match:\ncolumns: {column_names}\nvalues: {values}"

    return {col: common.extract_value(val) for col, val in zip(column_names, values)}


def translate_insert(statement: token_groups.Statement) -> typing.List[QueryExpression]:
    """Translate a INSERT SQL query into an equivalent FQL query.

    Params:
    -------
    statement: An SQL statement returned by sqlparse.

    Returns:
    --------
    An FQL query expression.
    """
    sql_query = models.SQLQuery.from_statement(statement)
    table = sql_query.tables[0]

    _, value_group = statement.token_next_by(i=token_groups.Values)
    document_to_insert = _build_document(table, value_group)

    # Fauna's Select doesn't play nice with null values, so we have to wrap it in an
    # if/else if the underlying value & default are null
    get_field_value = lambda document, field_name, field_constraints: q.let(
        {
            "references": q.select("references", field_constraints, default={}),
            "default_value": q.select(
                "default", field_constraints, default=common.NULL
            ),
            "field_value": q.select(field_name, document, q.var("default_value")),
        },
        q.if_(
            q.equals(q.var("references"), {}),
            q.var("field_value"),
            common.get_foreign_key_ref(
                q.var("field_value"), q.select([0, 0], q.to_array(q.var("references")))
            ),
        ),
    )

    build_document = lambda metadata: q.let(
        {"document": document_to_insert},
        q.to_object(
            q.map_(
                q.lambda_(
                    ["field_name", "field_constraints"],
                    [
                        q.var("field_name"),
                        get_field_value(
                            q.var("document"),
                            q.var("field_name"),
                            q.var("field_constraints"),
                        ),
                    ],
                ),
                q.to_array(metadata),
            )
        ),
    )
    create_document = lambda collection, metadata: q.create(
        collection, {"data": build_document(metadata)}
    )

    flatten_response_fields = lambda response: q.to_object(
        q.union(
            q.map_(
                q.lambda_(
                    ["key", "value"],
                    q.if_(
                        q.equals(q.var("key"), common.DATA),
                        q.to_array(q.var("value")),
                        # We put single key/value pairs in nested arrays to match
                        # the structure of the nested 'data' key/values
                        [[q.var("key"), q.var("value")]],
                    ),
                ),
                q.to_array(response),
            )
        )
    )

    # We map over field_metadata, with the ref ID inserted first, to build the document object
    # in order to maintain the order of fields as queried. Otherwise, SQLAlchemy
    # gets confused and assigns values to the incorrect keys.
    get_collection_field_names = lambda metadata: q.union(
        ["ref"],
        q.map_(
            q.lambda_(["field", "_"], q.var("field")),
            q.to_array(metadata),
        ),
    )
    # We convert 'ref' back into 'id' in the response, because that's the primary key
    # that SQLAlchemy expects.
    get_response_field_name = lambda field_name: q.if_(
        q.equals(field_name, "ref"),
        "id",
        field_name,
    )
    get_response_field_value = lambda document, field_name: q.select(
        field_name, document, default=common.NULL
    )
    build_document_response = lambda document, metadata: q.to_object(
        q.map_(
            q.lambda_(
                "field_name",
                [
                    get_response_field_name(q.var("field_name")),
                    get_response_field_value(document, q.var("field_name")),
                ],
            ),
            get_collection_field_names(metadata),
        )
    )

    get_metadata = lambda collection: q.select(
        ["data", "metadata", "fields"],
        q.get(collection),
        default={},
    )

    return [
        q.let(
            {
                "collection": q.collection(table.name),
                "metadata": get_metadata(q.var("collection")),
                "document_response": create_document(
                    q.var("collection"), q.var("metadata")
                ),
                "document": flatten_response_fields(q.var("document_response")),
            },
            {"data": [build_document_response(q.var("document"), q.var("metadata"))]},
        )
    ]
