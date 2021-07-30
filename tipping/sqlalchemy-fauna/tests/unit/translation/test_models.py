# pylint: disable=missing-docstring,redefined-outer-name

import sqlparse
from sqlparse import sql as token_groups, tokens as token_types
import pytest
from faker import Faker

from sqlalchemy_fauna.fauna.translation import models
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

    column = models.Column.from_identifier(column_identifier)

    assert column.name == column_name
    assert column.table_name == expected_table_name
    assert column.alias == expected_alias


def test_column():
    column = models.Column(table_name="users", name="name", alias="alias")
    assert str(column) == "name"
    assert column.alias_map == {column.name: column.alias}

    table = models.Table(name="users", columns=[column])
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

    columns = models.Column.from_identifier_group(identifiers)

    for column in columns:
        assert column.name in expected_columns
        assert column.alias in expected_aliases


def test_table():
    table_name = "users"
    sql_query = f"SELECT users.name FROM {table_name}"
    statement = sqlparse.parse(sql_query)[0]
    _, column_identifier = statement.token_next_by(i=(token_groups.Identifier))

    column = models.Column.from_identifier(column_identifier)
    table = models.Table(name=table_name, columns=[column])
    assert table.name == table_name
    assert str(table) == table_name

    assert len(table.columns) == 1
    assert table.columns[0].name == column.name
    assert table.column_alias_map == {column.name: column.alias}


def test_table_from_identifier():
    table_name = "users"
    sql_query = f"SELECT users.name FROM {table_name}"
    statement = sqlparse.parse(sql_query)[0]
    idx, _ = statement.token_next_by(m=(token_types.Keyword, "FROM"))
    _, table_identifier = statement.token_next_by(i=(token_groups.Identifier), idx=idx)

    table = models.Table.from_identifier(table_identifier)
    assert table.name == table_name


def test_add_column():
    table_name = "users"
    sql_query = f"SELECT users.name FROM {table_name}"
    statement = sqlparse.parse(sql_query)[0]
    _, column_identifier = statement.token_next_by(i=(token_groups.Identifier))

    column = models.Column.from_identifier(column_identifier)
    table = models.Table(name=table_name)

    table.add_column(column)

    assert table.columns == [column]


def test_sql_query():
    sql_query = models.SQLQuery(tables=[models.Table(name="table")])
    assert len(sql_query.tables) == 1
    assert sql_query.tables[0].name == "table"


@pytest.mark.parametrize("distinct", ["DISTINCT", ""])
def test_sql_query_from_statement(distinct):
    table_name = "users"
    column_name = "name"
    sql_string = f"SELECT {distinct} users.{column_name} FROM {table_name}"
    statement = sqlparse.parse(sql_string)[0]

    sql_query = models.SQLQuery.from_statement(statement)
    table = sql_query.tables[0]
    column = table.columns[0]
    assert table.name == table_name
    assert column.name == column_name
    assert sql_query.distinct == bool(distinct)


@pytest.mark.parametrize(
    ["sql_string", "error_message"],
    [
        (
            "SELECT users.name, accounts.number from users, accounts",
            "Only one table per query is currently supported",
        ),
        # Using regex's "any character" symbol instead of the expected single-quotes,
        # because getting the escapes right through multiple layers of code is super annoying.
        ("SELECT * from users", "Wildcards (.*.) are not yet supported"),
    ],
)
def test_unsupported_sql_query_statements(sql_string, error_message):
    statement = sqlparse.parse(sql_string)[0]

    with pytest.raises(exceptions.NotSupportedError, match=error_message):
        models.SQLQuery.from_statement(statement)


def test_filter():
    column = models.Column(name="name", alias="name", table_name="users")
    operator = "="
    value = "Bob"
    where_filter = models.Filter(column=column, operator=operator, value=value)

    assert where_filter.column == column
    assert where_filter.operator == operator
    assert where_filter.value == value


select_values = "SELECT * FROM users"
where_not_equal_1 = select_values + f" WHERE users.age <> {Fake.pyint()}"
where_not_equal_2 = select_values + f" WHERE users.age != {Fake.pyint()}"
where_between = (
    select_values + f" WHERE users.age BETWEEN {Fake.pyint()} AND {Fake.pyint}"
)
where_like = select_values + f" WHERE users.name LIKE '%{Fake.first_name()}%'"
where_in = (
    select_values
    + f" WHERE users.name IN ('{Fake.first_name()}', '{Fake.first_name()}')"
)
where_or = (
    select_values
    + f" WHERE users.name = '{Fake.first_name()}' OR users.age = {Fake.pyint()}"
)


@pytest.mark.parametrize(
    ["sql_query", "error_message"],
    [
        (
            where_not_equal_1,
            "Only the following comparisons are supported in WHERE clauses",
        ),
        (
            where_not_equal_2,
            "Only the following comparisons are supported in WHERE clauses",
        ),
        (where_between, "BETWEEN not yet supported in WHERE clauses"),
        (
            where_like,
            "Only the following comparisons are supported in WHERE clauses",
        ),
        (where_in, "Only the following comparisons are supported in WHERE clauses"),
        (where_or, "OR not yet supported in WHERE clauses."),
    ],
)
def test_unsupported_filter_from_where_group(sql_query, error_message):
    statement = sqlparse.parse(sql_query)[0]
    _, where_group = statement.token_next_by(i=(token_groups.Where))

    with pytest.raises(exceptions.NotSupportedError, match=error_message):
        models.Filter.from_where_group(where_group)


where_id = select_values + f" WHERE users.id = '{Fake.credit_card_number}'"
where_equals = select_values + f" WHERE users.name = '{Fake.first_name()}'"
where_and = (
    where_equals
    + f" AND users.age = {Fake.pyint()} AND users.finger_count = {Fake.pyint()}"
)
where_greater = select_values + f" WHERE users.age > {Fake.pyint()}"
where_greater_equal = select_values + f" WHERE users.age >= {Fake.pyint()}"
where_less = select_values + f" WHERE users.age < {Fake.pyint()}"
where_less_equal = select_values + f" WHERE users.age <= {Fake.pyint()}"
where_is_null = select_values + " WHERE users.job IS NULL"
where_reverse_comparison = select_values + " WHERE 'Bob' = users.name"


@pytest.mark.parametrize(
    "sql_string",
    [
        select_values,
        where_id,
        where_equals,
        where_and,
        where_greater,
        where_greater_equal,
        where_less,
        where_less_equal,
        where_is_null,
        where_reverse_comparison,
    ],
)
def test_filter_from_where_group(sql_string):
    statement = sqlparse.parse(sql_string)[0]
    _, where_group = statement.token_next_by(i=(token_groups.Where))

    where_filters = models.Filter.from_where_group(where_group)
    for where_filter in where_filters:
        assert isinstance(where_filter, models.Filter)
