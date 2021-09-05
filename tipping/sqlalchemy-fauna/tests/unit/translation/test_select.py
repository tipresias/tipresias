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
@pytest.mark.parametrize(
    ["sql_query", "error_message"],
    [
        (select_sum, "SUM"),
        (select_avg, "AVG"),
        (
            "SELECT COUNT(users.id) FROM users JOIN accounts ON users.id = accounts.user_id",
            "SQL functions across multiple tables are not yet supported",
        ),
        (
            select_join_order_by,
            "we currently can only sort the principal table",
        ),
        (select_order_multiple, "Ordering by multiple columns is not yet supported"),
    ],
)
def test_translating_unsupported_select(sql_query, error_message):
    with pytest.raises(exceptions.NotSupportedError, match=error_message):
        select.translate_select(sqlparse.parse(sql_query)[0])


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
select_join_order_by_principal = (
    "SELECT users.name, accounts.number FROM users "
    "JOIN accounts ON users.id = accounts.user_id "
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
    ],
)
def test_translate_select(sql_string):
    fql_query = select.translate_select(sqlparse.parse(sql_string)[0])

    assert isinstance(fql_query, QueryExpression)
