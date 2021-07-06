"""Translate a INSERT SQL query into an equivalent FQL query."""

import typing
from datetime import datetime

from sqlparse import sql as token_groups
from sqlparse import tokens as token_types
from faunadb import query as q
from faunadb.objects import _Expr as QueryExpression

from sqlalchemy_fauna import exceptions
from .common import parse_identifiers, extract_value, get_foreign_key_ref


DATA_KEY = "data"
NULL = "NULL"


def _build_document(
    column_identifiers: typing.Union[
        token_groups.IdentifierList, token_groups.Identifier
    ],
    value_group: token_groups.Values,
    collection_name: str,
) -> typing.Dict[str, typing.Union[str, int, float, datetime, None, bool]]:
    table_field_map = parse_identifiers(column_identifiers, collection_name)
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
    column_names = table_field_map[collection_name].keys()

    assert len(column_names) == len(
        values
    ), f"Lengths didn't match:\ncolumns: {column_names}\nvalues: {values}"

    return {col: extract_value(val) for col, val in zip(column_names, values)}


def translate_insert(statement: token_groups.Statement) -> typing.List[QueryExpression]:
    """Translate a INSERT SQL query into an equivalent FQL query.

    Params:
    -------
    statement: An SQL statement returned by sqlparse.

    Returns:
    --------
    An FQL query expression.
    """
    idx, function_group = statement.token_next_by(i=token_groups.Function)

    if function_group is None:
        raise exceptions.NotSupportedError(
            "INSERT INTO statements without column names are not currently supported."
        )

    func_idx, table_identifier = function_group.token_next_by(i=token_groups.Identifier)
    collection_name = table_identifier.value

    _, column_group = function_group.token_next_by(
        i=token_groups.Parenthesis, idx=func_idx
    )
    _, column_identifiers = column_group.token_next_by(
        i=(token_groups.IdentifierList, token_groups.Identifier)
    )
    idx, value_group = statement.token_next_by(i=token_groups.Values, idx=idx)

    document_to_insert = _build_document(
        column_identifiers, value_group, collection_name
    )

    collection = q.get(q.collection(collection_name))
    field_metadata = q.select(["data", "metadata", "fields"], collection, default={})

    # Fauna's Select doesn't play nice with null values, so we have to wrap it in an
    # if/else if the underlying value & default are null
    get_field_value = lambda field_name, field_constraints: q.let(
        {
            "field_value": q.select(
                field_name,
                document_to_insert,
                q.select("default", field_constraints, default=NULL),
            )
        },
        q.if_(q.equals(q.var("field_value"), NULL), None, q.var("field_value")),
    )

    replace_foreign_key_with_ref = lambda field_value, field_constraints: q.let(
        {"references": q.select("references", field_constraints)},
        q.if_(
            q.equals(q.var("references"), {}),
            field_value,
            get_foreign_key_ref(field_value, q.var("references")),
        ),
    )

    document_to_create = q.to_object(
        q.map_(
            q.lambda_(
                ["field_name", "field_constraints"],
                [
                    q.var("field_name"),
                    replace_foreign_key_with_ref(
                        get_field_value(
                            q.var("field_name"), q.var("field_constraints")
                        ),
                        q.var("field_constraints"),
                    ),
                ],
            ),
            q.to_array(field_metadata),
        )
    )
    create_document = q.create(
        q.collection(collection_name), {"data": document_to_create}
    )

    flattened_items = q.union(
        q.map_(
            q.lambda_(
                ["key", "value"],
                q.if_(
                    q.equals(q.var("key"), DATA_KEY),
                    q.to_array(q.var("value")),
                    # We put single key/value pairs in nested arrays to match
                    # the structure of the nested 'data' key/values
                    [[q.var("key"), q.var("value")]],
                ),
            ),
            q.to_array(q.var("document")),
        )
    )

    # We map over field_metadata, with the ref ID inserted first, to build the document object
    # in order to maintain the order of fields as queried. Otherwise, SQLAlchemy
    # gets confused and assigns values to the incorrect keys.
    document_fields = q.union(
        ["ref"],
        q.map_(
            q.lambda_(["field", "_"], q.var("field")),
            q.to_array(field_metadata),
        ),
    )
    field_name = q.if_(
        q.equals(q.var("field"), "ref"),
        "id",
        q.var("field"),
    )
    field_value = q.select_with_default(
        q.var("field"), q.to_object(flattened_items), default=None
    )
    document_response = q.to_object(
        q.map_(
            q.lambda_("field", [field_name, field_value]),
            document_fields,
        )
    )

    return [q.let({"document": create_document}, {"data": [document_response]})]
