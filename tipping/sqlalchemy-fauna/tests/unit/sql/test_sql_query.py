# pylint: disable=missing-docstring,redefined-outer-name

import functools
from sqlalchemy_fauna.sql.sql_table import Table

import sqlparse
import pytest
from faker import Faker
import numpy as np

from tests.fixtures.factories import (
    FilterFactory,
    ColumnFactory,
    TableFactory,
    SQLQueryFactory,
)
from sqlalchemy_fauna.sql import sql_query
from sqlalchemy_fauna import exceptions


Fake = Faker()


class TestSQLQuery:
    @staticmethod
    def test_sql_query():
        table = TableFactory()
        query = sql_query.SQLQuery(
            "SELECT",
            tables=[table],
        )
        assert len(query.tables) == 1
        assert query.tables[0].name == table.name
        assert set(query.columns) == set(table.columns)

        assert query.alias_map == {
            table.name: {column.name: column.alias for column in table.columns}
        }

    @staticmethod
    def test_validation():
        table = TableFactory(columns__position=0, columns__count=2)
        with pytest.raises(AssertionError, match="must have unique position values"):
            sql_query.SQLQuery("SELECT", tables=[table])

    @staticmethod
    def test_add_filter_to_table():
        query = SQLQueryFactory()
        table = next(table for table in query.tables if table.has_columns)
        sql_filter = FilterFactory(column=np.random.choice(table.columns))

        query.add_filter_to_table(sql_filter)

        assert sql_filter in table.filters

    @staticmethod
    @pytest.mark.parametrize("distinct", ["DISTINCT", ""])
    def test_from_statement_distinct(distinct):
        table_name = "users"
        column_name = "name"
        sql_string = f"SELECT {distinct} users.{column_name} FROM {table_name}"
        statement = sqlparse.parse(sql_string)[0]

        query = sql_query.SQLQuery.from_statement(statement)

        assert query.distinct == bool(distinct)

    @staticmethod
    def test_from_statement_order_by():
        table_name = "users"
        column_names = ["name", "age"]
        order_by = "ORDER BY " + ", ".join(column_names)

        sql_string = f"SELECT users.name, users.age FROM {table_name} {order_by} DESC"
        statement = sqlparse.parse(sql_string)[0]

        query = sql_query.SQLQuery.from_statement(statement)

        for idx, column in enumerate(query.order_by.columns):
            assert column.name == column_names[idx]

    @staticmethod
    def test_from_statement_limit():
        table_name = "users"

        sql_string = f"SELECT users.name, users.age FROM {table_name} LIMIT 1"
        statement = sqlparse.parse(sql_string)[0]

        query = sql_query.SQLQuery.from_statement(statement)

        assert query.limit == 1

    @staticmethod
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
    def test_from_statement_insert(column_names, column_values, expected_values):
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

    @staticmethod
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
                "SELECT transactions.amount, transactions.number FROM users "
                "JOIN accounts ON users.id = accounts.user_id "
                "JOIN transactions ON accounts.id = transactions.account_id",
                ["users", "accounts", "transactions"],
                ["amount", "number"],
            ),
            (
                "SELECT users.age, users.name FROM users "
                "JOIN accounts ON users.id = accounts.user_id",
                ["users", "accounts"],
                ["age", "name"],
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
    def test_from_statement(sql_string, expected_table_names, expected_column_names):
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

    @staticmethod
    @pytest.mark.parametrize(
        ["sql_string", "error_message"],
        [
            (
                "SELECT users.name, users.age FROM users, accounts",
                "must join them together with a JOIN clause",
            ),
            (
                "SELECT users.name, accounts.number FROM users "
                "JOIN accounts ON users.id = accounts.user_id",
                "only queries that select or modify one table at a time are supported",
            ),
            # Using regex's "any character" symbol instead of the expected single-quotes,
            # because getting the escapes right through multiple layers of code is super annoying.
            ("SELECT * from users", "Wildcards (.*.) are not yet supported"),
            (
                "SELECT users.name, users.age FROM users "
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
    def test_unsupported_statement(sql_string, error_message):
        statement = sqlparse.parse(sql_string)[0]

        with pytest.raises(exceptions.NotSupportedError, match=error_message):
            sql_query.SQLQuery.from_statement(statement)


class TestOrderBy:
    @staticmethod
    @pytest.mark.parametrize(
        ["direction", "expected_direction"],
        [
            (sql_query.OrderDirection.DESC, sql_query.OrderDirection.DESC),
            (None, sql_query.OrderDirection.ASC),
        ],
    )
    def test_order_by(direction, expected_direction):
        columns = [ColumnFactory()]
        order_by = sql_query.OrderBy(columns=columns, direction=direction)

        assert order_by.columns == columns
        assert order_by.direction == expected_direction

    @staticmethod
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
    def test_from_statement(
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
