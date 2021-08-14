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
select_sum = "SELECT sum(users.id) AS sum_1 from users"
select_avg = "SELECT avg(users.id) AS avg_1 from users"
select_join_order_by = (
    "SELECT users.name, accounts.number FROM users "
    "JOIN accounts ON users.id = accounts.user_id "
    "ORDER BY accounts.number"
)
select_order_multiple = (
    "SELECT users.name, users.age FROM users ORDER BY users.name, users.age"
)
# These are meant to be examples of SQL queries that are not currently supported,
# but that are valid SQL and so should be supported eventually.
# Regarding some of the more esoteric queries (e.g. INFORMATION_SCHEMA), I'm not certain
# that they're valid, but can't be bothered to investigate further until it's actually
# relevant
@pytest.mark.parametrize(
    ["sql_query", "error_message"],
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
        (select_sum, "SUM"),
        (select_avg, "AVG"),
        (
            "SELECT COUNT(users.id) FROM users JOIN accounts ON users.id = accounts.user_id",
            "SQL functions across multiple tables are not yet supported",
        ),
        (
            select_join_order_by,
            "Either select one table at a time or remove the ordering constraint",
        ),
        (select_order_multiple, "Ordering by multiple columns is not yet supported"),
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
select_where_equals = select_values + " WHERE users.name = 'Bob'"
select_count = "SELECT count(users.id) AS count_1 FROM users"
select_join = (
    "SELECT users.name, accounts.number FROM users "
    "JOIN accounts ON users.id = accounts.user_id"
)
select_order_by = "SELECT users.name, users.age FROM users ORDER BY users.name"
select_order_by_desc = (
    "SELECT users.name, users.age FROM users ORDER BY users.name DESC"
)


@pytest.mark.parametrize(
    "sql_string",
    [
        select_info_schema_tables,
        select_info_schema_columns,
        select_info_schema_constraints,
        select_values,
        select_aliases,
        select_where_equals,
        select_count,
        select_join,
        select_order_by,
        select_order_by_desc,
    ],
)
def test_translate_select(sql_string):
    fql_queries = select.translate_select(sqlparse.parse(sql_string)[0])

    for fql_query in fql_queries:
        assert isinstance(fql_query, QueryExpression)
