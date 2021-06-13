"""Translate a SELECT SQL query into an equivalent FQL query."""

from typing import Tuple

from sqlparse import tokens as token_types
from sqlparse import sql as token_groups
from faunadb import query as q
from faunadb.objects import _Expr as QueryExpression

from sqlalchemy_fauna import exceptions
from .common import extract_value, parse_identifiers, ColumnNames, Aliases, parse_where


SelectReturn = Tuple[QueryExpression, ColumnNames, Aliases]


DATA_KEY = "data"


def _translate_select_from_table(statement: token_groups.Statement) -> SelectReturn:
    _, wildcard = statement.token_next_by(t=(token_types.Wildcard))

    if wildcard is not None:
        raise exceptions.NotSupportedError("Wildcards ('*') are not yet supported")

    idx, identifiers = statement.token_next_by(
        i=(token_groups.Identifier, token_groups.IdentifierList)
    )
    idx, _ = statement.token_next_by(m=(token_types.Keyword, "FROM"), idx=idx)
    idx, table_identifier = statement.token_next_by(
        i=(token_groups.Identifier), idx=idx
    )
    table_name = table_identifier.value
    table_field_map = parse_identifiers(identifiers, table_name)

    # We can only handle one table at a time for now
    if len(table_field_map.keys()) > 1:
        raise exceptions.NotSupportedError(
            "Only one table per query is currently supported"
        )

    _, where_group = statement.token_next_by(i=token_groups.Where, idx=idx)
    records_to_select = parse_where(where_group, table_name)

    document_items = q.to_array(q.get(q.var("document")))
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
            document_items,
        )
    )

    field_map = table_field_map[table_name]
    selected_fields = list(field_map.keys())
    field_alias = q.select_with_default(
        q.var("field"),
        field_map,
        default=q.var("field"),
    )
    field_value = q.select_with_default(
        q.var("field"),
        q.to_object(flattened_items),
        default=None,
    )
    translate_to_alias = q.lambda_("field", [field_alias, field_value])
    # We map over selected_fields to build document object to maintain the order
    # of fields as queried. Otherwise, SQLAlchemy gets confused and assigns values
    # to the incorrect keys.
    aliased_document = q.to_object(q.map_(translate_to_alias, selected_fields))

    return q.map_(
        q.lambda_("document", aliased_document),
        q.paginate(records_to_select),
    )


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

    return query


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
        ["data", "metadata", "fields"],
        q.get(q.collection(condition_value)),
    )

    return query


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


def translate_select(statement: token_groups.Statement) -> QueryExpression:
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
        return query

    if table_name == "INFORMATION_SCHEMA.COLUMNS":
        return _translate_select_from_info_schema_columns(statement)

    if table_name == "INFORMATION_SCHEMA.CONSTRAINT_TABLE_USAGE":
        return _translate_select_from_info_schema_constraints(statement)

    return _translate_select_from_table(statement)
