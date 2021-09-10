# pylint: disable=missing-docstring,redefined-outer-name

import functools
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


@pytest.mark.parametrize(
    ["column_sql_string", "error_message"],
    [("SUM(users.id) AS sum_1", "SUM"), ("AVG(users.id) AS avg_1", "AVG")],
)
def test_unsupported_column_from_identifier(column_sql_string, error_message):
    sql_string = f"SELECT {column_sql_string} FROM users"
    statement = sqlparse.parse(sql_string)[0]
    _, column_identifier = statement.token_next_by(i=(token_groups.Identifier))

    with pytest.raises(exceptions.NotSupportedError, match=error_message):
        models.Column.from_identifier(column_identifier)


def test_column_from_comparison_group():
    sql_string = "UPDATE users SET users.name = 'Bob'"
    statement = sqlparse.parse(sql_string)[0]
    _, comparison_group = statement.token_next_by(i=token_groups.Comparison)

    column = models.Column.from_comparison_group(comparison_group)

    assert column.name == "name"
    assert column.table_name == "users"
    assert column.value == "Bob"


def test_unsupported_column_from_comparison_group():
    sql_string = "UPDATE users SET users.name = users.occupation"
    statement = sqlparse.parse(sql_string)[0]
    _, comparison_group = statement.token_next_by(i=token_groups.Comparison)

    with pytest.raises(
        exceptions.NotSupportedError,
        match="Only updating to literal values is currently supported",
    ):
        models.Column.from_comparison_group(comparison_group)


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
    sql_query = f"SELECT users.name FROM {table_name} WHERE users.name = 'Bob'"
    statement = sqlparse.parse(sql_query)[0]
    _, column_identifier = statement.token_next_by(i=(token_groups.Identifier))
    _, where_group = statement.token_next_by(i=(token_groups.Where))

    column = models.Column.from_identifier(column_identifier)
    sql_filters = models.Filter.from_where_group(where_group)
    table = models.Table(name=table_name, columns=[column], filters=sql_filters)
    assert table.name == table_name
    assert str(table) == table_name

    assert len(table.columns) == 1
    assert table.columns[0].name == column.name
    assert table.column_alias_map == {column.name: column.alias}

    assert len(table.filters) == 1
    assert table.filters[0].value == sql_filters[0].value


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


def test_add_filter():
    table_name = "users"
    sql_query = f"SELECT users.name FROM {table_name} WHERE users.age > 30"
    statement = sqlparse.parse(sql_query)[0]
    _, where_group = statement.token_next_by(i=(token_groups.Where))

    sql_filters = models.Filter.from_where_group(where_group)
    table = models.Table(name=table_name)

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

    table = models.Table(name=table_name)
    foreign_table = models.Table(name=foreign_table_name)

    table.add_join(foreign_table, comparison_group, models.JoinDirection.RIGHT)

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

    table = models.Table(name=table_name)
    foreign_table = models.Table(name=foreign_table_name)

    with pytest.raises(
        exceptions.NotSupportedError, match="Table joins are only permitted on IDs"
    ):
        table.add_join(foreign_table, comparison_group, models.JoinDirection.RIGHT)


def test_sql_query():
    table_name = Fake.word()
    column_name = Fake.word()
    sql_query = models.SQLQuery(
        tables=[models.Table(name=table_name)],
        columns=[models.Column(name=column_name, alias=Fake.word())],
    )
    assert len(sql_query.tables) == 1
    assert sql_query.tables[0].name == table_name
    assert len(sql_query.columns) == 1
    assert sql_query.columns[0].name == column_name


def test_sql_add_filter_to_table():
    column = models.Column(table_name="users", name="name", alias="name")
    table = models.Table(name="users", columns=[column])
    sql_query = models.SQLQuery(tables=[table])
    sql_filter = models.Filter(column=column, operator="=", value="Bob")

    sql_query.add_filter_to_table(sql_filter)

    assert table.filters[0] == sql_filter


@pytest.mark.parametrize("distinct", ["DISTINCT", ""])
def test_sql_query_from_statement_distinct(distinct):
    table_name = "users"
    column_name = "name"
    sql_string = f"SELECT {distinct} users.{column_name} FROM {table_name}"
    statement = sqlparse.parse(sql_string)[0]

    sql_query = models.SQLQuery.from_statement(statement)

    assert sql_query.distinct == bool(distinct)


def test_sql_query_from_statement_order_by():
    table_name = "users"
    column_names = ["name", "age"]
    order_by = "ORDER BY " + ", ".join(column_names)

    sql_string = f"SELECT users.name, users.age FROM {table_name} {order_by} DESC"
    statement = sqlparse.parse(sql_string)[0]

    sql_query = models.SQLQuery.from_statement(statement)

    for idx, column in enumerate(sql_query.order_by.columns):
        assert column.name == column_names[idx]


def test_sql_query_from_statement_limit():
    table_name = "users"

    sql_string = f"SELECT users.name, users.age FROM {table_name} LIMIT 1"
    statement = sqlparse.parse(sql_string)[0]

    sql_query = models.SQLQuery.from_statement(statement)

    assert sql_query.limit == 1


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

    sql_query = models.SQLQuery.from_statement(statement)

    query_table_names = [table.name for table in sql_query.tables]
    assert query_table_names == [table_name]

    query_column_names, query_column_values = zip(
        *[(col.name, col.value) for col in sql_query.columns]
    )
    table_column_names = functools.reduce(
        lambda col_names, table: col_names + [col.name for col in table.columns],
        sql_query.tables,
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
    sql_query = models.SQLQuery.from_statement(statement)

    query_table_names = [table.name for table in sql_query.tables]
    assert query_table_names == expected_table_names

    query_column_names = [col.name for col in sql_query.columns]
    table_column_names = functools.reduce(
        lambda col_names, table: col_names + [col.name for col in table.columns],
        sql_query.tables,
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


@pytest.mark.parametrize(
    ["direction", "expected_direction"],
    [
        (models.OrderDirection.DESC, models.OrderDirection.DESC),
        (None, models.OrderDirection.ASC),
    ],
)
def test_order_by(direction, expected_direction):
    columns = [models.Column(name=Fake.word(), alias=Fake.word())]
    order_by = models.OrderBy(columns=columns, direction=direction)

    assert order_by.columns == columns
    assert order_by.direction == expected_direction


@pytest.mark.parametrize(
    ["sql_string", "expected_type", "expected_columns", "expected_direction"],
    [
        (
            "SELECT * FROM users ORDER BY users.name",
            models.OrderBy,
            ["name"],
            models.OrderDirection.ASC,
        ),
        (
            "SELECT * FROM users ORDER BY users.name DESC",
            models.OrderBy,
            ["name"],
            models.OrderDirection.DESC,
        ),
        (
            "SELECT * FROM users ORDER BY users.name, users.age",
            models.OrderBy,
            ["name", "age"],
            models.OrderDirection.ASC,
        ),
        (
            "SELECT * FROM users ORDER BY users.name, users.age ASC",
            models.OrderBy,
            ["name", "age"],
            models.OrderDirection.ASC,
        ),
        ("SELECT * FROM users", None, None, None),
    ],
)
def test_order_by_from_statement(
    sql_string, expected_type, expected_columns, expected_direction
):
    statement = sqlparse.parse(sql_string)[0]
    order_by = models.OrderBy.from_statement(statement)

    if expected_type:
        assert isinstance(order_by, expected_type)
        column_names = [column.name for column in order_by.columns]
        assert column_names == expected_columns
        assert order_by.direction == expected_direction
    else:
        assert order_by is None
