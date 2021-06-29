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


def get_foreign_key_ref(
    foreign_value: typing.Any, references: typing.Any
) -> QueryExpression:
    """Get the Ref to a document associated with a foreign key value.

    Params:
    -------
    foreign_value: The value to look up, usually an ID.
    references: Field metadata dict that defines the collection (key) and field name (value)
        that the foreign key refers to.

    Returns:
    --------
    Fauna query expression that returns an array of Refs for the associated document(s).
    """
    assert isinstance(foreign_value, str)
    return q.let(
        {
            # Assumes that there is only one reference per foreign key
            # and that it refers to the associated collection's ID field.
            # This is enforced via NotSupported errors when creating collections.
            "reference": q.union(q.to_array(references)),
            "foreign_collection": q.collection(q.select(0, q.var("reference"))),
        },
        q.ref(q.var("foreign_collection"), foreign_value),
    )


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


def _parse_is_null(
    where_group: token_groups.Where,
    collection_name: str,
    starting_idx: typing.Optional[int],
) -> QueryExpression:
    idx = starting_idx or 0
    idx, comparison_identifier = where_group.token_next_by(
        i=token_groups.Identifier, idx=idx
    )
    table_field_map = _parse_identifier({collection_name: {}}, comparison_identifier)
    field_names = list(table_field_map[collection_name].keys())
    assert len(field_names) == 1
    field_name = field_names[0]

    idx, is_keyword = where_group.token_next(idx, skip_ws=True, skip_cm=True)
    idx, null_keyword = where_group.token_next(idx, skip_ws=True, skip_cm=True)

    assert (
        is_keyword
        and is_keyword.value == "IS"
        and null_keyword
        and null_keyword.value == "NULL"
    )

    convert_to_ref_set = lambda index_match: q.join(
        index_match,
        q.lambda_(
            ["value", "ref"],
            q.match(q.index(f"{collection_name}_by_ref_terms"), q.var("ref")),
        ),
    )
    comparison_value = None
    equality_range = q.range(
        q.match(q.index(f"{collection_name}_by_{field_name}")),
        [comparison_value],
        [comparison_value],
    )

    return q.if_(
        q.exists(q.index(f"{collection_name}_by_{field_name}_terms")),
        q.match(
            q.index(f"{collection_name}_by_{field_name}_terms"),
            comparison_value,
        ),
        convert_to_ref_set(equality_range),
    )


def _parse_comparison(
    comparison_group: token_groups.Comparison, collection_name: str
) -> QueryExpression:
    _, comparison_identifier = comparison_group.token_next_by(i=token_groups.Identifier)
    table_field_map = _parse_identifier({collection_name: {}}, comparison_identifier)
    field_names = list(table_field_map[collection_name].keys())
    assert len(field_names) == 1
    field_name = field_names[0]

    comp_idx, comparison = comparison_group.token_next_by(t=token_types.Comparison)
    value_idx, comparison_check = comparison_group.token_next_by(t=token_types.Literal)

    if comparison_check is None:
        raise exceptions.NotSupportedError(
            "Only single, literal values are permitted for comparisons "
            "in WHERE clauses."
        )
    comparison_value = extract_value(comparison_check)

    convert_to_ref_set = lambda index_match: q.join(
        index_match,
        q.lambda_(
            ["value", "ref"],
            q.match(q.index(f"{collection_name}_by_ref_terms"), q.var("ref")),
        ),
    )

    get_collection_fields = lambda name: q.select(
        ["data", "metadata", "fields"], q.get(q.collection(name))
    )

    equality_range = q.range(
        q.match(q.index(f"{collection_name}_by_{field_name}")),
        [comparison_value],
        [comparison_value],
    )

    if comparison.value == "=":
        if field_name == "ref":
            assert isinstance(comparison_value, str)
            return q.singleton(q.ref(q.collection(collection_name), comparison_value))

        return q.let(
            {
                "ref_index": q.index(f"{collection_name}_by_{field_name}_refs"),
                "term_index": q.index(f"{collection_name}_by_{field_name}_terms"),
                "references": q.select(
                    [field_name, "references"], get_collection_fields(collection_name)
                ),
            },
            q.if_(
                q.exists(q.var("ref_index")),
                q.match(
                    q.var("ref_index"),
                    get_foreign_key_ref(comparison_value, q.var("references")),
                ),
                q.if_(
                    q.exists(q.var("term_index")),
                    q.match(
                        q.var("term_index"),
                        comparison_value,
                    ),
                    convert_to_ref_set(equality_range),
                ),
            ),
        )

    if comparison.value in [">=", ">"]:
        field_value_greater_than_literal = value_idx > comp_idx

        if field_value_greater_than_literal:
            inclusive_comparison_range = q.range(
                q.match(q.index(f"{collection_name}_by_{field_name}")),
                [comparison_value],
                [],
            )
        else:
            inclusive_comparison_range = q.range(
                q.match(q.index(f"{collection_name}_by_{field_name}")),
                [],
                [comparison_value],
            )

        if comparison.value == ">=":
            return convert_to_ref_set(inclusive_comparison_range)

        return convert_to_ref_set(
            q.difference(inclusive_comparison_range, equality_range)
        )

    if comparison.value in ["<=", "<"]:
        field_value_less_than_literal = value_idx > comp_idx

        if field_value_less_than_literal:
            inclusive_comparison_range = q.range(
                q.match(q.index(f"{collection_name}_by_{field_name}")),
                [],
                [comparison_value],
            )
        else:
            inclusive_comparison_range = q.range(
                q.match(q.index(f"{collection_name}_by_{field_name}")),
                [comparison_value],
                [],
            )

        if comparison.value == "<=":
            return convert_to_ref_set(inclusive_comparison_range)

        return convert_to_ref_set(
            q.difference(inclusive_comparison_range, equality_range)
        )

    raise exceptions.NotSupportedError(
        "Only the following comparisons are supported in WHERE clauses: "
        "'=', '>', '>=', '<', '<='"
    )


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

    comparisons = []
    comparison_idx = 0

    while True:
        and_idx, and_keyword = where_group.token_next_by(
            m=(token_types.Keyword, "AND"), idx=comparison_idx
        )
        should_have_and_keyword = comparison_idx > 0
        comparison_idx, comparison = where_group.token_next_by(
            m=(token_types.Keyword, "IS"), i=token_groups.Comparison, idx=comparison_idx
        )

        if comparison is None:
            break

        assert not should_have_and_keyword or (
            should_have_and_keyword and and_keyword is not None
        )

        comparison_query = (
            _parse_is_null(where_group, collection_name, and_idx)
            if comparison.value == "IS"
            else _parse_comparison(comparison, collection_name)
        )
        comparisons.append(comparison_query)

    return q.intersection(*comparisons)
