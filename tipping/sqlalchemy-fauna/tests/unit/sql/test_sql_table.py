# pylint: disable=missing-docstring,redefined-outer-name

import sqlparse
from sqlparse import sql as token_groups, tokens as token_types
import pytest
from faker import Faker

from sqlalchemy_fauna.sql import sql_table
from sqlalchemy_fauna import exceptions


Fake = Faker()


column_name = "name"


@pytest.mark.parametrize(
    ["column_sql", "expected_table_name", "expected_alias"],
    [
        (f"users.{column_name}", "users", column_name),
        (column_name, None, column_name),
        (f"users.{column_name} AS user_name", "users", "user_name"),
    ],
)
def test_column_from_identifier(column_sql, expected_table_name, expected_alias):
    sql_query = f"SELECT {column_sql} FROM users"
    statement = sqlparse.parse(sql_query)[0]
    _, column_identifier = statement.token_next_by(i=(token_groups.Identifier))

    column = sql_table.Column.from_identifier(column_identifier)

    assert column.name == column_name
    assert column.table_name == expected_table_name
    assert column.alias == expected_alias
    assert column.position == 0


@pytest.mark.parametrize(
    ["column_sql", "expected_name", "expected_function"],
    [
        (
            f"count(users.{column_name})",
            f"count(users.{column_name})",
            sql_table.Function.COUNT,
        ),
    ],
)
def test_column_from_function_identifier(column_sql, expected_name, expected_function):
    sql_string = f"SELECT {column_sql} FROM users"
    statement = sqlparse.parse(sql_string)[0]
    _, column_function = statement.token_next_by(i=(token_groups.Function))

    column = sql_table.Column.from_identifier(
        token_groups.Identifier([column_function]), 0
    )

    assert column.name == expected_name
    assert column.function_name == expected_function.value
    assert column.position == 0


@pytest.mark.parametrize(
    ["column_sql_string", "error_message"],
    [("SUM(users.id) AS sum_1", "SUM"), ("AVG(users.id) AS avg_1", "AVG")],
)
def test_unsupported_column_from_identifier(column_sql_string, error_message):
    sql_string = f"SELECT {column_sql_string} FROM users"
    statement = sqlparse.parse(sql_string)[0]
    _, column_identifier = statement.token_next_by(i=(token_groups.Identifier))

    with pytest.raises(exceptions.NotSupportedError, match=error_message):
        sql_table.Column.from_identifier(column_identifier)


def test_column_from_comparison_group():
    sql_string = "UPDATE users SET users.name = 'Bob'"
    statement = sqlparse.parse(sql_string)[0]
    _, comparison_group = statement.token_next_by(i=token_groups.Comparison)

    column = sql_table.Column.from_comparison_group(comparison_group)

    assert column.name == "name"
    assert column.table_name == "users"
    assert column.value == "Bob"
    assert column.position == 0


def test_unsupported_column_from_comparison_group():
    sql_string = "UPDATE users SET users.name = users.occupation"
    statement = sqlparse.parse(sql_string)[0]
    _, comparison_group = statement.token_next_by(i=token_groups.Comparison)

    with pytest.raises(
        exceptions.NotSupportedError,
        match="Only updating to literal values is currently supported",
    ):
        sql_table.Column.from_comparison_group(comparison_group)


def test_column():
    column = sql_table.Column(
        position=0, table_name="users", name="name", alias="alias"
    )
    assert str(column) == "name"
    assert column.alias_map == {column.name: column.alias}

    table = sql_table.Table(name="users", columns=[column])
    column.table = table
    assert column.table_name == table.name


table_name = "users"
select_single_column = f"SELECT {table_name}.id FROM {table_name}"
select_columns = f"SELECT {table_name}.id, {table_name}.name FROM {table_name}"
select_aliases = (
    f"SELECT {table_name}.id AS user_id, {table_name}.name AS user_name "
    "FROM {table_name}"
)
select_function = f"SELECT count({table_name}.id) FROM {table_name}"
select_function_alias = (
    f"SELECT count({table_name}.id) AS count_{table_name} FROM {table_name}"
)
insert = "INSERT INTO users (name, age, finger_count) VALUES ('Bob', 30, 10)"


@pytest.mark.parametrize(
    ["sql_query", "expected_columns", "expected_aliases"],
    [
        (select_single_column, ["ref"], ["id"]),
        (select_columns, ["ref", "name"], ["id", "name"]),
        (select_aliases, ["ref", "name"], ["user_id", "user_name"]),
        (select_function, [f"count({table_name}.id)"], [f"count({table_name}.id)"]),
        (select_function_alias, [f"count({table_name}.id)"], [f"count_{table_name}"]),
        (insert, ["name", "age", "finger_count"], ["name", "age", "finger_count"]),
    ],
)
def test_from_identifier_group(sql_query, expected_columns, expected_aliases):
    statement = sqlparse.parse(sql_query)[0]
    _, identifiers = statement.token_next_by(
        i=(token_groups.Identifier, token_groups.IdentifierList, token_groups.Function)
    )

    columns = sql_table.Column.from_identifier_group(identifiers)

    for column in columns:
        assert column.name in expected_columns
        assert column.alias in expected_aliases


def test_table():
    table_name = "users"
    sql_query = f"SELECT users.name FROM {table_name} WHERE users.name = 'Bob'"
    statement = sqlparse.parse(sql_query)[0]
    _, column_identifier = statement.token_next_by(i=(token_groups.Identifier))
    _, where_group = statement.token_next_by(i=(token_groups.Where))

    column = sql_table.Column.from_identifier(column_identifier)
    sql_filters = sql_table.Filter.from_where_group(where_group)
    table = sql_table.Table(name=table_name, columns=[column], filters=sql_filters)
    assert table.name == table_name
    assert str(table) == table_name

    assert len(table.columns) == 1
    assert table.columns[0].name == column.name
    assert table.alias_map == {table.name: {column.name: column.alias}}

    assert len(table.filters) == 1
    assert table.filters[0].value == sql_filters[0].value


def test_table_from_identifier():
    table_name = "users"
    sql_query = f"SELECT users.name FROM {table_name}"
    statement = sqlparse.parse(sql_query)[0]
    idx, _ = statement.token_next_by(m=(token_types.Keyword, "FROM"))
    _, table_identifier = statement.token_next_by(i=(token_groups.Identifier), idx=idx)

    table = sql_table.Table.from_identifier(table_identifier)
    assert table.name == table_name


def test_add_column():
    table_name = "users"
    sql_query = f"SELECT users.name FROM {table_name}"
    statement = sqlparse.parse(sql_query)[0]
    _, column_identifier = statement.token_next_by(i=(token_groups.Identifier))

    column = sql_table.Column.from_identifier(column_identifier)
    table = sql_table.Table(name=table_name)

    table.add_column(column)

    assert table.columns == [column]


def test_add_filter():
    table_name = "users"
    sql_query = f"SELECT users.name FROM {table_name} WHERE users.age > 30"
    statement = sqlparse.parse(sql_query)[0]
    _, where_group = statement.token_next_by(i=(token_groups.Where))

    sql_filters = sql_table.Filter.from_where_group(where_group)
    table = sql_table.Table(name=table_name)

    table.add_filter(sql_filters[0])

    assert table.filters == sql_filters


def test_add_join():
    table_name = "users"
    foreign_table_name = "accounts"
    sql_query = (
        f"SELECT {table_name}.name, {foreign_table_name}.amount "
        f"FROM {table_name} JOIN {foreign_table_name} "
        f"ON {table_name}.id = {foreign_table_name}.user_id"
    )
    statement = sqlparse.parse(sql_query)[0]
    _, comparison_group = statement.token_next_by(i=(token_groups.Comparison))

    table = sql_table.Table(name=table_name)
    foreign_table = sql_table.Table(name=foreign_table_name)

    table.add_join(foreign_table, comparison_group, sql_table.JoinDirection.RIGHT)

    assert table.right_join_table == foreign_table
    assert table.right_join_key.name == "ref"
    assert foreign_table.left_join_table == table
    assert foreign_table.left_join_key.name == "user_id"


def test_invalid_add_join():
    table_name = "users"
    foreign_table_name = "accounts"
    sql_query = (
        f"SELECT {table_name}.name, {foreign_table_name}.amount "
        f"FROM {table_name} JOIN {foreign_table_name} "
        f"ON {table_name}.name = {foreign_table_name}.user_name"
    )
    statement = sqlparse.parse(sql_query)[0]
    _, comparison_group = statement.token_next_by(i=(token_groups.Comparison))

    table = sql_table.Table(name=table_name)
    foreign_table = sql_table.Table(name=foreign_table_name)

    with pytest.raises(
        exceptions.NotSupportedError, match="Table joins are only permitted on IDs"
    ):
        table.add_join(foreign_table, comparison_group, sql_table.JoinDirection.RIGHT)
