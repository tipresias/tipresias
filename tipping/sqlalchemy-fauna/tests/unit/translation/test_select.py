# pylint: disable=missing-docstring,redefined-outer-name

import pytest
from faunadb.objects import _Expr as QueryExpression
import sqlparse

from sqlalchemy_fauna.fauna.translation import select
from sqlalchemy_fauna import exceptions

select_values = (
    "SELECT users.id, users.name, users.date_joined, users.age, users.finger_count "
    "FROM users"
)

partial_select_info_schema_columns = "SELECT * FROM INFORMATION_SCHEMA.COLUMNS"
partial_select_info_schema_constraints = (
    "SELECT * FROM INFORMATION_SCHEMA.CONSTRAINT_TABLE_USAGE"
)
select_multiple_tables = "SELECT * FROM users, accounts"
select_where_greater = select_values + " WHERE users.age > 30"
select_where_greater_equal = select_values + " WHERE users.age >= 30"
select_where_less = select_values + " WHERE users.age < 30"
select_where_less_equal = select_values + " WHERE users.age <= 30"
select_where_not_equal_1 = select_values + " WHERE users.age <> 30"
select_where_not_equal_2 = select_values + " WHERE users.age != 30"
select_where_between = select_values + " WHERE users.age BETWEEN 30 AND 40"
select_where_like = select_values + " WHERE users.name LIKE '%Bob%'"
select_where_in = select_values + " WHERE users.name IN ('Bob', 'Linda')"
select_or = select_values + " WHERE users.name = 'Bob' OR users.age = 30"
select_all = "SELECT * FROM users"

# These are meant to be examples of SQL queries that are not currently supported,
# but that are valid SQL and so should be supported eventually.
# Regarding some of the more esoteric queries (e.g. INFORMATION_SCHEMA), I'm not certain
# that they're valid, but can't be bothered to investigate further until it's actually
# relevant
@pytest.mark.parametrize(
    "sql_query,error_message",
    [
        (
            partial_select_info_schema_columns,
            "'WHERE TABLE_NAME = <table_name>' clause is required",
        ),
        (
            partial_select_info_schema_constraints,
            "'WHERE TABLE_NAME = <table_name>' clause is required",
        ),
        (
            partial_select_info_schema_columns + " WHERE user.name = 'Bob'",
            "Only TABLE_NAME condition is supported",
        ),
        (
            partial_select_info_schema_constraints + " WHERE user.name = 'Bob'",
            "Only TABLE_NAME condition is supported",
        ),
        (
            partial_select_info_schema_columns + " WHERE TABLE_NAME LIKE 'users'",
            "Only column-value-based conditions",
        ),
        (
            partial_select_info_schema_constraints + " WHERE TABLE_NAME LIKE 'users'",
            "Only column-value-based conditions",
        ),
        (select_multiple_tables, "Only one table per query is currently supported"),
        (
            select_where_greater,
            "Only column-value equality conditions are currently supported",
        ),
        (
            select_where_greater_equal,
            "Only column-value equality conditions are currently supported",
        ),
        (
            select_where_less,
            "Only column-value equality conditions are currently supported",
        ),
        (
            select_where_less_equal,
            "Only column-value equality conditions are currently supported",
        ),
        (
            select_where_not_equal_1,
            "Only column-value equality conditions are currently supported",
        ),
        (
            select_where_not_equal_2,
            "Only column-value equality conditions are currently supported",
        ),
        (
            select_where_between,
            "BETWEEN not yet supported in WHERE clauses",
        ),
        (
            select_where_like,
            "Only column-value equality conditions are currently supported",
        ),
        (
            select_where_in,
            "Only column-value equality conditions are currently supported",
        ),
        (select_or, "OR not yet supported in WHERE clauses."),
        (select_all, "Wildcards"),
    ],
)
def test_translating_unsupported_select(sql_query, error_message):
    with pytest.raises(exceptions.NotSupportedError, match=error_message):
        select.translate_select(sqlparse.parse(sql_query)[0])


select_info_schema_tables = "SELECT * FROM INFORMATION_SCHEMA.TABLES"
select_info_schema_columns = (
    partial_select_info_schema_columns + " WHERE TABLE_NAME = 'users'"
)
select_info_schema_constraints = (
    partial_select_info_schema_constraints + " WHERE TABLE_NAME = 'users'"
)
select_aliases = (
    "SELECT users.id AS users_id, users.name AS users_name, "
    "users.date_joined AS users_date_joined, users.age AS users_age, "
    "users.finger_count AS users_finger_count "
    "FROM users"
)
select_where = select_values + " WHERE users.name = 'Bob'"
select_and = select_where + " AND users.age = 45 AND users.finger_count = 10"


@pytest.mark.parametrize(
    "sql_query",
    [
        select_info_schema_tables,
        select_info_schema_columns,
        select_info_schema_constraints,
        select_values,
        select_aliases,
        select_where,
        select_and,
    ],
)
def test_translate_select(sql_query):
    fql_query, _, _ = select.translate_select(sqlparse.parse(sql_query)[0])
    assert isinstance(fql_query, QueryExpression)
