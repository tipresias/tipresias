"""Translate a INSERT SQL query into an equivalent FQL query."""

from sqlparse import sql as token_groups
from sqlparse import tokens as token_types
from faunadb import query as q
from faunadb.objects import _Expr as QueryExpression

from sqlalchemy_fauna import exceptions
from .common import parse_identifiers, extract_value


def translate_insert(statement: token_groups.Statement) -> QueryExpression:
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
    table_name = table_identifier.value

    _, column_group = function_group.token_next_by(
        i=token_groups.Parenthesis, idx=func_idx
    )
    _, column_identifiers = column_group.token_next_by(
        i=(token_groups.IdentifierList, token_groups.Identifier)
    )
    _, column_names, _ = parse_identifiers(column_identifiers)

    idx, value_group = statement.token_next_by(i=token_groups.Values, idx=idx)
    _, parenthesis_group = value_group.token_next_by(i=token_groups.Parenthesis)
    value_identifiers = parenthesis_group.flatten()

    values = [
        value
        for value in value_identifiers
        if not value.ttype == token_types.Punctuation and not value.is_whitespace
    ]

    assert len(column_names) == len(
        values
    ), f"Lengths didn't match:\ncolumns: {column_names}\nvalues: {values}"

    record_to_insert = {
        col: extract_value(val) for col, val in zip(column_names, values)
    }

    collection = q.get(q.collection(table_name))
    field_metadata = q.to_array(
        q.select(["data", "metadata", "fields"], collection, default=[])
    )

    get_field_value = lambda doc: q.select(
        q.var("field_name"),
        doc,
        q.select("default", q.var("field_constraints")),
    )
    fill_blank_values_with_defaults = lambda doc: q.lambda_(
        ["field_name", "field_constraints"],
        [q.var("field_name"), get_field_value(doc)],
    )

    document_to_create = q.to_object(
        q.map_(
            fill_blank_values_with_defaults(record_to_insert),
            field_metadata,
        )
    )

    return q.create(q.collection(table_name), {"data": document_to_create})
