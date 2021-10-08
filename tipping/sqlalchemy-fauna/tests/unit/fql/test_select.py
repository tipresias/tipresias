# pylint: disable=missing-docstring,redefined-outer-name

import pytest
from faunadb.objects import _Expr as QueryExpression
import sqlparse

from sqlalchemy_fauna.fauna.fql import select
from sqlalchemy_fauna import exceptions, sql

select_values = (
    "SELECT users.id, users.name, users.date_joined, users.age, users.finger_count "
    "FROM users"
)

select_sum = "SELECT sum(users.id) AS sum_1 from users"
select_avg = "SELECT avg(users.id) AS avg_1 from users"
select_join_order_by = (
    "SELECT accounts.name, accounts.number FROM users "
    "JOIN accounts ON users.id = accounts.user_id "
    "ORDER BY users.id"
)
select_order_multiple = (
    "SELECT users.name, users.age FROM users ORDER BY users.name, users.age"
)
# These are meant to be examples of SQL queries that are not currently supported,
# but that are valid SQL and so should be supported eventually.
@pytest.mark.parametrize(
    ["sql_string", "error_message"],
    [
        (select_sum, "SUM"),
        (select_avg, "AVG"),
        (
            select_join_order_by,
            "we currently can only sort the principal table",
        ),
        (select_order_multiple, "Ordering by multiple columns is not yet supported"),
    ],
)
def test_translating_unsupported_select(sql_string, error_message):
    with pytest.raises(exceptions.NotSupportedError, match=error_message):
        sql_statement = sqlparse.parse(sql_string)[0]
        sql_query = sql.SQLQuery.from_statement(sql_statement)
        select.translate_select(sql_query)


select_aliases = (
    "SELECT users.id AS users_id, users.name AS users_name, "
    "users.date_joined AS users_date_joined, users.age AS users_age, "
    "users.finger_count AS users_finger_count "
    "FROM users"
)
select_where_equals = select_values + " WHERE users.name = 'Bob'"
select_count = "SELECT count(users.id) AS count_1 FROM users"
select_join = (
    "SELECT users.name, users.age FROM users "
    "JOIN accounts ON users.id = accounts.user_id "
    "WHERE accounts.amount > 5.0"
)
select_order_by = "SELECT users.name, users.age FROM users ORDER BY users.name"
select_order_by_desc = (
    "SELECT users.name, users.age FROM users ORDER BY users.name DESC"
)
select_join_order_by_principal = (
    "SELECT users.name, users.age FROM users "
    "JOIN accounts ON users.id = accounts.user_id "
    "WHERE accounts.amount > 5.0 "
    "ORDER BY users.name"
)


@pytest.mark.parametrize(
    "sql_string",
    [
        select_values,
        select_aliases,
        select_where_equals,
        select_count,
        select_join,
        select_order_by,
        select_order_by_desc,
        select_join_order_by_principal,
        (
            "SELECT COUNT(users.id) FROM users JOIN accounts ON users.id = accounts.user_id "
            "WHERE accounts.amount > 5.0"
        ),
    ],
)
def test_translate_select(sql_string):
    sql_statement = sqlparse.parse(sql_string)[0]
    sql_query = sql.SQLQuery.from_statement(sql_statement)
    fql_query = select.translate_select(sql_query)

    assert isinstance(fql_query, QueryExpression)
