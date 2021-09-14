# pylint: disable=missing-docstring,redefined-outer-name

import functools

import sqlparse
from sqlparse import sql as token_groups
import pytest
from faker import Faker

from sqlalchemy_fauna.sql import sql_query, sql_table
from sqlalchemy_fauna import exceptions


Fake = Faker()


def test_sql_query():
    table_name = Fake.word()
    column_name = Fake.word()
    column_alias = Fake.word()
    query = sql_query.SQLQuery(
        tables=[
            sql_table.Table(
                name=table_name,
                columns=[
                    sql_table.Column(name=column_name, alias=column_alias, position=0)
                ],
            )
        ],
    )
    assert len(query.tables) == 1
    assert query.tables[0].name == table_name
    assert len(query.columns) == 1
    assert query.columns[0].name == column_name

    assert query.alias_map == {table_name: {column_name: column_alias}}


def test_sql_query_validation():
    with pytest.raises(AssertionError, match="must have unique position values"):
        sql_query.SQLQuery(
            tables=[
                sql_table.Table(
                    name=Fake.word(),
                    columns=[
                        sql_table.Column(
                            name=Fake.word(), alias=Fake.word(), position=0
                        ),
                        sql_table.Column(
                            name=Fake.word(), alias=Fake.word(), position=0
                        ),
                    ],
                )
            ],
        )


def test_sql_add_filter_to_table():
    column = sql_table.Column(table_name="users", name="name", alias="name", position=0)
    table = sql_table.Table(name="users", columns=[column])
    query = sql_query.SQLQuery(tables=[table])
    sql_filter = sql_table.Filter(column=column, operator="=", value="Bob")

    query.add_filter_to_table(sql_filter)

    assert table.filters[0] == sql_filter


@pytest.mark.parametrize("distinct", ["DISTINCT", ""])
def test_sql_query_from_statement_distinct(distinct):
    table_name = "users"
    column_name = "name"
    sql_string = f"SELECT {distinct} users.{column_name} FROM {table_name}"
    statement = sqlparse.parse(sql_string)[0]

    query = sql_query.SQLQuery.from_statement(statement)

    assert query.distinct == bool(distinct)


def test_sql_query_from_statement_order_by():
    table_name = "users"
    column_names = ["name", "age"]
    order_by = "ORDER BY " + ", ".join(column_names)

    sql_string = f"SELECT users.name, users.age FROM {table_name} {order_by} DESC"
    statement = sqlparse.parse(sql_string)[0]

    query = sql_query.SQLQuery.from_statement(statement)

    for idx, column in enumerate(query.order_by.columns):
        assert column.name == column_names[idx]


def test_sql_query_from_statement_limit():
    table_name = "users"

    sql_string = f"SELECT users.name, users.age FROM {table_name} LIMIT 1"
    statement = sqlparse.parse(sql_string)[0]

    query = sql_query.SQLQuery.from_statement(statement)

    assert query.limit == 1


@pytest.mark.parametrize(
    ["column_names", "column_values", "expected_values"],
    [
        (
            ["name", "age", "finger_count", "job", "has_mustache"],
            ["'Bob'", "30", "10", "NONE", "TRUE"],
            ["Bob", 30, 10, None, True],
        ),
        (["name"], ["'Bob'"], ["Bob"]),
    ],
)
def test_sql_query_from_statement_insert(column_names, column_values, expected_values):
    table_name = "users"

    sql_string = (
        f"INSERT INTO {table_name} ({', '.join(column_names)}) "
        f"VALUES ({', '.join(column_values)})"
    )
    statement = sqlparse.parse(sql_string)[0]

    query = sql_query.SQLQuery.from_statement(statement)

    query_table_names = [table.name for table in query.tables]
    assert query_table_names == [table_name]

    query_column_names, query_column_values = zip(
        *[(col.name, col.value) for col in query.columns]
    )
    table_column_names = functools.reduce(
        lambda col_names, table: col_names + [col.name for col in table.columns],
        query.tables,
        [],
    )
    assert set(query_column_names) == set(table_column_names)
    assert list(query_column_names) == column_names
    assert list(query_column_values) == expected_values


@pytest.mark.parametrize(
    ["sql_string", "expected_table_names", "expected_column_names"],
    [
        (
            "SELECT users.id, users.name, users.date_joined, users.age, users.finger_count "
            "FROM users",
            ["users"],
            ["ref", "name", "date_joined", "age", "finger_count"],
        ),
        (
            "SELECT users.name, transactions.number, users.age FROM users "
            "JOIN accounts ON users.id = accounts.user_id "
            "JOIN transactions ON accounts.id = transactions.account_id",
            ["users", "accounts", "transactions"],
            ["name", "number", "age"],
        ),
        (
            "SELECT accounts.number, users.name FROM users "
            "JOIN accounts ON users.id = accounts.user_id",
            ["users", "accounts"],
            ["number", "name"],
        ),
        ("DELETE FROM users", ["users"], []),
        ("UPDATE users SET users.name = 'Bob'", ["users"], ["name"]),
        (
            "UPDATE users SET users.name = 'Bob', users.age = 40",
            ["users"],
            ["name", "age"],
        ),
    ],
)
def test_sql_query_from_statement(
    sql_string, expected_table_names, expected_column_names
):
    statement = sqlparse.parse(sql_string)[0]
    query = sql_query.SQLQuery.from_statement(statement)

    query_table_names = [table.name for table in query.tables]
    assert query_table_names == expected_table_names

    query_column_names = [col.name for col in query.columns]
    table_column_names = functools.reduce(
        lambda col_names, table: col_names + [col.name for col in table.columns],
        query.tables,
        [],
    )
    assert set(query_column_names) == set(table_column_names)
    assert query_column_names == expected_column_names


@pytest.mark.parametrize(
    ["sql_string", "error_message"],
    [
        (
            "SELECT users.name, accounts.number FROM users, accounts",
            "must join them together with a JOIN clause",
        ),
        # Using regex's "any character" symbol instead of the expected single-quotes,
        # because getting the escapes right through multiple layers of code is super annoying.
        ("SELECT * from users", "Wildcards (.*.) are not yet supported"),
        (
            "SELECT users.name, accounts.number FROM users "
            "JOIN accounts ON users.name = accounts.user_name",
            "Table joins are only permitted on IDs and foreign keys that refer to IDs",
        ),
        (
            "INSERT INTO users VALUES ('Bob', 30, 10)",
            "INSERT INTO statements without column names are not currently supported",
        ),
        (
            "INSERT INTO users (name, age) VALUES ('Bob', 45), ('Linda', 45), ('Tina', 14)",
            "INSERT for multiple rows is not supported yet",
        ),
    ],
)
def test_unsupported_sql_query_statements(sql_string, error_message):
    statement = sqlparse.parse(sql_string)[0]

    with pytest.raises(exceptions.NotSupportedError, match=error_message):
        sql_query.SQLQuery.from_statement(statement)


def test_filter():
    column = sql_table.Column(name="name", alias="name", table_name="users", position=0)
    operator = "="
    value = "Bob"
    where_filter = sql_table.Filter(column=column, operator=operator, value=value)

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
        sql_table.Filter.from_where_group(where_group)


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

    where_filters = sql_table.Filter.from_where_group(where_group)
    for where_filter in where_filters:
        assert isinstance(where_filter, sql_table.Filter)


@pytest.mark.parametrize(
    ["direction", "expected_direction"],
    [
        (sql_query.OrderDirection.DESC, sql_query.OrderDirection.DESC),
        (None, sql_query.OrderDirection.ASC),
    ],
)
def test_order_by(direction, expected_direction):
    columns = [sql_table.Column(name=Fake.word(), alias=Fake.word(), position=0)]
    order_by = sql_query.OrderBy(columns=columns, direction=direction)

    assert order_by.columns == columns
    assert order_by.direction == expected_direction


@pytest.mark.parametrize(
    ["sql_string", "expected_type", "expected_columns", "expected_direction"],
    [
        (
            "SELECT * FROM users ORDER BY users.name",
            sql_query.OrderBy,
            ["name"],
            sql_query.OrderDirection.ASC,
        ),
        (
            "SELECT * FROM users ORDER BY users.name DESC",
            sql_query.OrderBy,
            ["name"],
            sql_query.OrderDirection.DESC,
        ),
        (
            "SELECT * FROM users ORDER BY users.name, users.age",
            sql_query.OrderBy,
            ["name", "age"],
            sql_query.OrderDirection.ASC,
        ),
        (
            "SELECT * FROM users ORDER BY users.name, users.age ASC",
            sql_query.OrderBy,
            ["name", "age"],
            sql_query.OrderDirection.ASC,
        ),
        ("SELECT * FROM users", None, None, None),
    ],
)
def test_order_by_from_statement(
    sql_string, expected_type, expected_columns, expected_direction
):
    statement = sqlparse.parse(sql_string)[0]
    order_by = sql_query.OrderBy.from_statement(statement)

    if expected_type:
        assert isinstance(order_by, expected_type)
        column_names = [column.name for column in order_by.columns]
        assert column_names == expected_columns
        assert order_by.direction == expected_direction
    else:
        assert order_by is None
