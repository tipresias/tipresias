# pylint: disable=missing-docstring,redefined-outer-name

import pytest
from faunadb.objects import _Expr as QueryExpression

from sqlalchemy_fauna.fauna import translation
from sqlalchemy_fauna import exceptions


def test_format_sql_query():
    sql_query = (
        "SELECT users.id, users.name, users.date_joined, users.age, users.finger_count "
        "FROM users"
    )
    expected_sql_string = (
        "SELECT users.id,\n"
        "       users.name,\n"
        "       users.date_joined,\n"
        "       users.age,\n"
        "       users.finger_count\n"
        "FROM users"
    )

    assert translation.format_sql_query(sql_query) == expected_sql_string


# TODO: this is valid SQL that we might eventually want to support
def test_translate_sql_to_fql_multiple():
    sql_query = (
        "SELECT users.id, users.name, users.date_joined, users.age, users.finger_count "
        "FROM users;"
        "SELECT users.password, users.favorites FROM users"
    )

    with pytest.raises(
        exceptions.NotSupportedError,
        match="Only one SQL statement at a time is currently supported",
    ):
        translation.translate_sql_to_fql(sql_query)


def test_translate_sql_to_fql_select():
    sql_query = (
        "SELECT users.id, users.name, users.date_joined, users.age, users.finger_count "
        "FROM users"
    )
    fql_queries = translation.translate_sql_to_fql(sql_query)

    for fql_query in fql_queries:
        assert isinstance(fql_query, QueryExpression)


def test_translate_sql_to_fql_create():
    sql_query = (
        "CREATE TABLE users (id INTEGER NOT NULL, "
        "name VARCHAR, date_joined DATETIME NOT NULL, "
        "age INTEGER, finger_count INTEGER, PRIMARY KEY (id), UNIQUE (name))"
    )
    fql_queries = translation.translate_sql_to_fql(sql_query)

    for fql_query in fql_queries:
        assert isinstance(fql_query, QueryExpression)


def test_translate_sql_to_fql_drop():
    sql_query = "DROP TABLE users"
    fql_queries = translation.translate_sql_to_fql(sql_query)

    for fql_query in fql_queries:
        assert isinstance(fql_query, QueryExpression)


def test_translate_sql_to_fql_insert():
    sql_query = "INSERT INTO users (name, age, finger_count) VALUES ('Bob', 30, 10)"
    fql_queries = translation.translate_sql_to_fql(sql_query)

    for fql_query in fql_queries:
        assert isinstance(fql_query, QueryExpression)


def test_translate_sql_to_fql_delete():
    sql_query = "DELETE FROM users"
    fql_queries = translation.translate_sql_to_fql(sql_query)

    for fql_query in fql_queries:
        assert isinstance(fql_query, QueryExpression)


def test_translate_sql_to_fql_update():
    sql_query = "UPDATE users SET users.name = 'Bob'"
    fql_queries = translation.translate_sql_to_fql(sql_query)

    for fql_query in fql_queries:
        assert isinstance(fql_query, QueryExpression)
