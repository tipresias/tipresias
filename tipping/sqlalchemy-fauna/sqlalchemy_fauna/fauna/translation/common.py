"""Shared SQL translations and utilities for various statement types."""

import typing
import re
from datetime import datetime, timezone
from warnings import warn
from dateutil import parser

from sqlparse import sql as token_groups
from sqlparse import tokens as token_types
from mypy_extensions import TypedDict
from faunadb.objects import _Expr as QueryExpression
from faunadb import query as q

from sqlalchemy_fauna import exceptions
from . import models

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


NULL = "NULL"
DATA = "data"


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
    except (parser.ParserError, ValueError, _NumericString):
        pass

    return string_value


def get_foreign_key_ref(
    foreign_value: QueryExpression,
    references: QueryExpression,
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
    return q.let(
        {
            # Assumes that there is only one reference per foreign key
            # and that it refers to the associated collection's ID field
            # (e.g. {'associated_table': 'id'}).
            # This is enforced via NotSupported errors when creating collections.
            "references": q.union(q.to_array(references)),
            "reference_collection": q.select(0, q.var("references"), default=NULL),
            "is_blank_reference": q.or_(
                q.is_null(foreign_value),
                q.equals(foreign_value, NULL),
                q.equals(q.var("reference_collection"), NULL),
            ),
        },
        q.if_(
            q.var("is_blank_reference"),
            None,
            q.ref(q.collection(q.var("reference_collection")), foreign_value),
        ),
    )


def _parse_is_null(
    where_group: token_groups.Where,
    table: models.Table,
    starting_idx: typing.Optional[int],
) -> QueryExpression:
    idx = starting_idx or 0
    idx, comparison_identifier = where_group.token_next_by(
        i=token_groups.Identifier, idx=idx
    )
    columns = models.Column.from_identifier_group(comparison_identifier)
    assert len(columns) == 1
    table.add_column(columns[0])
    field_name = columns[0].name

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
            q.match(q.index(f"{table.name}_by_ref_terms"), q.var("ref")),
        ),
    )
    comparison_value = None
    equality_range = q.range(
        q.match(q.index(f"{table.name}_by_{field_name}")),
        [comparison_value],
        [comparison_value],
    )

    return q.if_(
        q.exists(q.index(f"{table.name}_by_{field_name}_terms")),
        q.match(
            q.index(f"{table.name}_by_{field_name}_terms"),
            comparison_value,
        ),
        convert_to_ref_set(equality_range),
    )


def _parse_comparison(
    comparison_group: token_groups.Comparison, table: models.Table
) -> QueryExpression:
    _, comparison_identifier = comparison_group.token_next_by(i=token_groups.Identifier)
    columns = models.Column.from_identifier_group(comparison_identifier)
    assert len(columns) == 1
    table.add_column(columns[0])
    field_name = columns[0].name

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
            q.match(q.index(f"{table.name}_by_ref_terms"), q.var("ref")),
        ),
    )

    get_collection_fields = lambda name: q.select(
        [DATA, "metadata", "fields"], q.get(q.collection(name))
    )

    equality_range = q.range(
        q.match(q.index(f"{table.name}_by_{field_name}")),
        [comparison_value],
        [comparison_value],
    )

    if comparison.value == "=":
        if field_name == "ref":
            assert isinstance(comparison_value, str)
            return q.singleton(q.ref(q.collection(table.name), comparison_value))

        return q.let(
            {
                "ref_index": q.index(f"{table.name}_by_{field_name}_refs"),
                "term_index": q.index(f"{table.name}_by_{field_name}_terms"),
                "references": q.select(
                    [field_name, "references"],
                    get_collection_fields(table.name),
                    default={},
                ),
                "comparison_value": comparison_value,
            },
            q.if_(
                q.exists(q.var("ref_index")),
                q.match(
                    q.var("ref_index"),
                    get_foreign_key_ref(q.var("comparison_value"), q.var("references")),
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
                q.match(q.index(f"{table.name}_by_{field_name}")),
                [comparison_value],
                [],
            )
        else:
            inclusive_comparison_range = q.range(
                q.match(q.index(f"{table.name}_by_{field_name}")),
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
                q.match(q.index(f"{table.name}_by_{field_name}")),
                [],
                [comparison_value],
            )
        else:
            inclusive_comparison_range = q.range(
                q.match(q.index(f"{table.name}_by_{field_name}")),
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
    where_group: token_groups.Where, table: models.Table
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
        return q.intersection(q.match(q.index(f"all_{table.name}")))

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
            _parse_is_null(where_group, table, and_idx)
            if comparison.value == "IS"
            else _parse_comparison(comparison, table)
        )
        comparisons.append(comparison_query)

    return q.intersection(*comparisons)
