# pylint: disable=missing-docstring,redefined-outer-name

import sqlparse
from sqlparse import sql as token_groups
import pytest
from sqlalchemy_fauna.fauna.translation import models


@pytest.mark.parametrize(
    ["column_sql", "expected_table_name", "expected_alias"],
    [
        ("users.name", "users", None),
        ("name", None, None),
        ("users.name AS user_name", "users", "user_name"),
    ],
)
def test_column(column_sql, expected_table_name, expected_alias):
    sql_query = f"SELECT {column_sql} FROM users"
    statement = sqlparse.parse(sql_query)[0]
    idx, column_identifier = statement.token_next_by(i=(token_groups.Identifier))
    _, table_identifier = statement.token_next_by(i=(token_groups.Identifier), idx=idx)

    column = models.Column(column_identifier)

    assert column.name == "name"
    assert column.table_name == expected_table_name
    assert column.alias == expected_alias

    table = models.Table(table_identifier, columns=[column])
    column.table = table
    assert column.table_name == table.name


def test_table():
    table_name = "users"
    sql_query = f"SELECT users.name FROM {table_name}"
    statement = sqlparse.parse(sql_query)[0]
    idx, column_identifier = statement.token_next_by(i=(token_groups.Identifier))
    _, table_identifier = statement.token_next_by(i=(token_groups.Identifier), idx=idx)

    column = models.Column(column_identifier)
    table = models.Table(table_identifier, columns=[column])
    assert table.name == table_name
    assert len(table.columns) == 1
    assert table.columns[0].name == column.name


def test_add_column():
    table_name = "users"
    sql_query = f"SELECT users.name FROM {table_name}"
    statement = sqlparse.parse(sql_query)[0]
    idx, column_identifier = statement.token_next_by(i=(token_groups.Identifier))
    _, table_identifier = statement.token_next_by(i=(token_groups.Identifier), idx=idx)

    column = models.Column(column_identifier)
    table = models.Table(table_identifier)

    table.add_column(column)

    assert table.columns == [column]
