"""Shared SQL translations and utilities for various statement types."""

import typing
import re
from datetime import datetime, timezone
from warnings import warn
from functools import reduce
from dateutil import parser

from sqlparse import sql as token_groups
from sqlparse import tokens as token_types
from sqlparse.tokens import _TokenType as TokenType
from mypy_extensions import TypedDict
from faunadb.objects import _Expr as QueryExpression
from faunadb import query as q

from sqlalchemy_fauna import exceptions

TableNames = typing.Sequence[typing.Optional[str]]
ColumnNames = typing.Sequence[str]
Aliases = typing.Sequence[typing.Optional[str]]
IdentifierValues = typing.Tuple[TableNames, ColumnNames, Aliases]

IndexComparison = typing.Tuple[str, typing.Union[int, float, str, None, bool, datetime]]
Comparisons = TypedDict(
    "Comparisons",
    {
        "by_id": typing.Optional[typing.Union[int, str]],
        "by_index": typing.List[IndexComparison],
    },
)

FieldAliasMap = typing.Dict[str, str]
TableFieldMap = typing.Dict[typing.Optional[str], FieldAliasMap]


class _NumericString(Exception):
    pass


def _parse_date_value(value):
    try:
        int(value)
        float(value)
        raise _NumericString()
    except ValueError:
        pass

    # We use isoparse instaed of parse, because the latter is too flexible
    # and will parse strings that aren't intended as datetime. Datetime strings
    # should always be in ISO format, because that's how we clean them in the dbapi.
    date_value = parser.isoparse(value)

    if date_value.tzinfo is None:
        warn(
            "Received a timezone-naive datetime value. Fauna only supports "
            "UTC timestamps, so converting to UTC."
        )
        return date_value.replace(tzinfo=timezone.utc)

    return date_value.astimezone(timezone.utc)


def _parse_identifier(
    table_field_map: TableFieldMap,
    identifier: typing.Union[token_groups.Identifier, TokenType],
) -> TableFieldMap:
    if not isinstance(identifier, token_groups.Identifier):
        return table_field_map

    idx, identifier_name = identifier.token_next_by(
        t=token_types.Name, i=token_groups.Function
    )

    tok_idx, next_token = identifier.token_next(idx, skip_ws=True)
    if next_token and next_token.match(token_types.Punctuation, "."):
        idx = tok_idx
        table_name = identifier_name.value
        idx, column_identifier = identifier.token_next_by(t=token_types.Name, idx=idx)
        column_name = column_identifier.value
    else:
        table_name = None
        column_name = identifier_name.value

    idx, as_keyword = identifier.token_next_by(m=(token_types.Keyword, "AS"), idx=idx)

    if as_keyword is not None:
        _, alias_identifier = identifier.token_next_by(
            i=token_groups.Identifier, idx=idx
        )
        alias_name = alias_identifier.value
    else:
        alias_name = column_name

    if table_name is None:
        assert len(table_field_map.keys()) == 1
        return {
            key: {**value, column_name: alias_name}
            for key, value in table_field_map.items()
        }

    # Fauna doesn't have an 'id' field, so we extract the ID value from the 'ref' included
    # in query responses, but we still want to map the field name to aliases as with other
    # fields for consistency when passing results to SQLAlchemy
    field_map_key = "ref" if column_name == "id" else column_name
    return {
        **table_field_map,
        table_name: {**table_field_map.get(table_name, {}), field_map_key: alias_name},
    }


def extract_value(
    token: token_groups.Token,
) -> typing.Union[str, int, float, None, bool, datetime]:
    """ "Get the raw value from an SQL token.

    Params:
    -------
    token: An SQL token created by sqlparse.

    Returns:
    --------
    Raw token value of the relevant Python data type.
    """
    value = token.value

    if value.upper() == "NONE":
        return None

    if value.upper() == "TRUE":
        return True

    if value.upper() == "FALSE":
        return False

    if "." in value:
        try:
            return float(value)
        except ValueError:
            pass

    try:
        return int(value)
    except ValueError:
        pass

    # sqlparse leaves ' characters around string values in the SQL, so we strip them out.
    string_value = re.sub("^'|'$", "", value)

    try:
        return _parse_date_value(string_value)
    # Seems that mypy can't find the very real ParserError
    except (parser.ParserError, ValueError, _NumericString):  # type: ignore
        pass

    return string_value


def parse_identifiers(
    identifiers: typing.Union[
        token_groups.Identifier, token_groups.IdentifierList, token_groups.Function
    ],
    table_name: typing.Optional[str] = None,
) -> TableFieldMap:
    """Extract raw table name, column name, and alias from SQL identifiers.

    Params:
    -------
    identifiers: Either a single identifier or identifier list.

    Returns:
    --------
    typing.Tuple of table_names, column names, and column aliases.
    """
    if isinstance(identifiers, token_groups.Function):
        return _parse_identifier(
            {table_name: {}}, token_groups.Identifier([identifiers])
        )

    if isinstance(identifiers, token_groups.Identifier):
        return _parse_identifier({table_name: {}}, identifiers)

    return reduce(_parse_identifier, identifiers, {table_name: {}})


def parse_where(
    where_group: token_groups.Where, collection_name: str
) -> QueryExpression:
    """Convert an SQL WHERE clause into an FQL match query.

    Params:
    -------
    where_group: An SQL token group representing a WHERE clause.

    Returns:
    --------
    FQL query expression that matches on the same conditions as the WHERE clause.
    """
    if where_group is None:
        return q.intersection(q.match(q.index(f"all_{collection_name}")))

    _, or_keyword = where_group.token_next_by(m=(token_types.Keyword, "OR"))

    if or_keyword is not None:
        raise exceptions.NotSupportedError("OR not yet supported in WHERE clauses.")

    _, between_keyword = where_group.token_next_by(m=(token_types.Keyword, "BETWEEN"))

    if between_keyword is not None:
        raise exceptions.NotSupportedError(
            "BETWEEN not yet supported in WHERE clauses."
        )

    comparisons: Comparisons = {"by_id": None, "by_index": []}
    matched_records = []
    condition_idx = 0

    while True:
        _, and_keyword = where_group.token_next_by(m=(token_types.Keyword, "AND"))
        should_have_and_keyword = condition_idx > 0
        condition_idx, condition = where_group.token_next_by(
            i=token_groups.Comparison, idx=condition_idx
        )

        if condition is None:
            break

        assert not should_have_and_keyword or (
            should_have_and_keyword and and_keyword is not None
        )

        _, column = condition.token_next_by(i=token_groups.Identifier)
        # Assumes column has form <table_name>.<column_name>
        condition_column = column.tokens[-1]

        _, comparison = condition.token_next_by(t=token_types.Comparison)

        if comparison.value == "=":
            _, condition_check = condition.token_next_by(t=token_types.Literal)
            condition_value = extract_value(condition_check)

            column_name = str(condition_column.value)

            if column_name == "id":
                assert isinstance(condition_value, str)
                matched_records.append(
                    q.singleton(q.ref(q.collection(collection_name), condition_value))
                )
            else:
                matched_records.append(
                    q.match(
                        q.index(f"{collection_name}_by_{column_name}"),
                        condition_value,
                    )
                )
                comparisons["by_index"].append((column_name, condition_value))
        else:
            raise exceptions.NotSupportedError(
                "Only column-value equality conditions are currently supported"
            )

    return q.intersection(*matched_records)
