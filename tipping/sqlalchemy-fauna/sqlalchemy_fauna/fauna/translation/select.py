"""Translate a SELECT SQL query into an equivalent FQL query."""

from typing import Union, Tuple, Optional, List
from datetime import datetime

from sqlparse import tokens as token_types
from sqlparse import sql as token_groups
from faunadb import query as q
from faunadb.objects import _Expr as QueryExpression
from mypy_extensions import TypedDict

from sqlalchemy_fauna import exceptions
from .common import extract_value, parse_identifiers, ColumnNames, Aliases

IndexComparison = Tuple[str, Union[int, float, str, None, bool, datetime]]
Comparisons = TypedDict(
    "Comparisons",
    {"by_id": Optional[Union[int, str]], "by_index": List[IndexComparison]},
)

SelectReturn = Tuple[QueryExpression, ColumnNames, Aliases]


def _matched_records(
    collection_name: str, comparisons: Optional[Comparisons]
) -> QueryExpression:
    if comparisons is None:
        return q.intersection(q.match(q.index(f"all_{collection_name}")))

    matched_records = []

    if comparisons["by_id"] is not None:
        if any(comparisons["by_index"]):
            raise exceptions.NotSupportedError(
                "When querying by ID, including other conditions in the WHERE "
                "clause is not supported."
            )

        return q.ref(q.collection(collection_name), comparisons["by_id"])

    for comparison_field, comparison_value in comparisons["by_index"]:
        matched_records.append(
            q.match(
                q.index(f"{collection_name}_by_{comparison_field}"),
                comparison_value,
            )
        )

    return q.intersection(*matched_records)


def _extract_where_conditions(statement) -> Optional[Comparisons]:
    _, where_group = statement.token_next_by(i=token_groups.Where)

    if where_group is None:
        return None

    _, or_keyword = where_group.token_next_by(m=(token_types.Keyword, "OR"))

    if or_keyword is not None:
        raise exceptions.NotSupportedError("OR not yet supported in WHERE clauses.")

    _, between_keyword = where_group.token_next_by(m=(token_types.Keyword, "BETWEEN"))

    if between_keyword is not None:
        raise exceptions.NotSupportedError(
            "BETWEEN not yet supported in WHERE clauses."
        )

    comparisons: Comparisons = {"by_id": None, "by_index": []}
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

        _, equals = condition.token_next_by(m=(token_types.Comparison, "="))
        if equals is None:
            raise exceptions.NotSupportedError(
                "Only column-value equality conditions are currently supported"
            )

        _, condition_check = condition.token_next_by(t=token_types.Literal)
        condition_value = extract_value(condition_check)

        column_name = str(condition_column.value)

        if column_name == "id":
            assert isinstance(condition_value, str)
            comparisons["by_id"] = condition_value
        else:
            comparisons["by_index"].append((column_name, condition_value))

    return comparisons


def _translate_select_from_table(statement: token_groups.Statement) -> SelectReturn:
    _, wildcard = statement.token_next_by(t=(token_types.Wildcard))

    if wildcard is not None:
        raise exceptions.NotSupportedError("Wildcards ('*') are not yet supported")

    idx, identifiers = statement.token_next_by(
        i=(token_groups.Identifier, token_groups.IdentifierList)
    )
    table_names, column_names, alias_names = parse_identifiers(identifiers)

    # We can only handle one table at a time for now
    if len(set(table_names)) > 1:
        raise exceptions.NotSupportedError(
            "Only one table per query is currently supported"
        )

    idx, _ = statement.token_next_by(m=(token_types.Keyword, "FROM"), idx=idx)
    _, table_identifier = statement.token_next_by(i=(token_groups.Identifier), idx=idx)
    table_name = table_identifier.value

    comparisons = _extract_where_conditions(statement)
    records_to_select = _matched_records(table_name, comparisons)

    query = q.map_(
        q.lambda_("document", q.get(q.var("document"))),
        q.paginate(records_to_select),
    )

    return (query, column_names, alias_names)


def _translate_select_from_info_schema_constraints(
    statement: token_groups.Statement,
) -> SelectReturn:
    # We don't use the standard logic for parsing this WHERE clause,
    # because sqlparse treats WHERE clauses in INFORMATION_SCHEMA queries
    # differently, returning flat tokens in the WHERE group
    # instead of nested token groups.
    _, where_group = statement.token_next_by(i=token_groups.Where)

    if where_group is None:
        raise exceptions.NotSupportedError(
            "A 'WHERE TABLE_NAME = <table_name>' clause is required when querying "
            "'INFORMATION_SCHEMA.CONSTRAINT_TABLE_USAGE'"
        )

    idx, condition_column = where_group.token_next_by(
        m=(token_types.Keyword, "TABLE_NAME")
    )

    if condition_column is None:
        raise exceptions.NotSupportedError(
            "Only TABLE_NAME condition is supported for "
            "SELECT FROM INFORMATION_SCHEMA.CONSTRAINT_TABLE_USAGE"
        )

    idx, condition = where_group.token_next_by(m=(token_types.Comparison, "="), idx=idx)

    if condition is None:
        raise exceptions.NotSupportedError(
            "Only column-value-based conditions (e.g. WHERE <column> = <value>) "
            "are currently supported."
        )

    _, condition_check = where_group.token_next(idx, skip_ws=True)
    condition_value = extract_value(condition_check)

    is_based_on_collection = q.lambda_(
        "index",
        q.equals(
            q.select(["source", "id"], q.get(q.var("index"))),
            condition_value,
        ),
    )
    indexes_based_on_collection = q.filter_(
        is_based_on_collection,
        q.paginate(q.indexes()),
    )

    query = q.map_(
        q.lambda_("index", q.get(q.var("index"))),
        indexes_based_on_collection,
    )

    return (query, [], [])


def _translate_select_from_info_schema_columns(
    statement: token_groups.Statement,
) -> SelectReturn:
    # We don't use the standard logic for parsing this WHERE clause,
    # because sqlparse treats WHERE clauses in INFORMATION_SCHEMA queries
    # differently, returning flat tokens in the WHERE group
    # instead of nested token groups.
    _, where_group = statement.token_next_by(i=token_groups.Where)

    if where_group is None:
        raise exceptions.NotSupportedError(
            "A 'WHERE TABLE_NAME = <table_name>' clause is required when querying "
            "'INFORMATION_SCHEMA.COLUMNS'"
        )

    idx, condition_column = where_group.token_next_by(
        m=(token_types.Keyword, "TABLE_NAME")
    )

    if condition_column is None:
        raise exceptions.NotSupportedError(
            "Only TABLE_NAME condition is supported for SELECT COLUMN_NAME"
        )

    idx, condition = where_group.token_next_by(m=(token_types.Comparison, "="), idx=idx)

    if condition is None:
        raise exceptions.NotSupportedError(
            "Only column-value-based conditions (e.g. WHERE <column> = <value>) "
            "are currently supported."
        )

    _, condition_check = where_group.token_next(idx, skip_ws=True)
    condition_value = extract_value(condition_check)

    query = q.select(
        ["data", "metadata", "fields"], q.get(q.collection(condition_value))
    )

    return (query, [], [])


def _extract_table_name(statement: token_groups.Statement) -> str:
    idx, _ = statement.token_next_by(m=(token_types.Keyword, "FROM"))
    _, table_identifier = statement.token_next_by(i=(token_groups.Identifier), idx=idx)

    if table_identifier is None:
        _, table_identifier_list = statement.token_next_by(
            i=(token_groups.IdentifierList), idx=idx
        )

        if table_identifier_list is not None:
            raise exceptions.NotSupportedError(
                "Only one table per query is currently supported"
            )
    return table_identifier.value


def translate_select(statement: token_groups.Statement) -> SelectReturn:
    """Translate a SELECT SQL query into an equivalent FQL query.

    Params:
    -------
    statement: An SQL statement returned by sqlparse.

    Returns:
    --------
    A tuple of FQL query expression, selected column  names, and their aliases.
    """
    table_name = _extract_table_name(statement)

    # TODO: As I've looked into INFORMATION_SCHEMA queries more, I realise
    # that these aren't returning valid responses for the given SQL queries,
    # but just the data that SQLAlchemy needs for some of the Dialect methods.
    # It's okay for now, but should probably fix these query responses eventually
    # and put the SQLAlchemy-specific logic/transformation in FaunaDialect
    if table_name == "INFORMATION_SCHEMA.TABLES":
        query = q.map_(
            q.lambda_("collection", q.get(q.var("collection"))),
            q.paginate(q.collections()),
        )
        return (query, [], [])

    if table_name == "INFORMATION_SCHEMA.COLUMNS":
        return _translate_select_from_info_schema_columns(statement)

    if table_name == "INFORMATION_SCHEMA.CONSTRAINT_TABLE_USAGE":
        return _translate_select_from_info_schema_constraints(statement)

    return _translate_select_from_table(statement)
