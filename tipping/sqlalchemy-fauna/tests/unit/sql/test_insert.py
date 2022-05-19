# pylint: disable=missing-docstring,redefined-outer-name

import pytest
import sqlparse

from sqlalchemy_fauna.sql import insert
from sqlalchemy_fauna import exceptions


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
def test_build_insert_table(column_names, column_values, expected_values):
    table_name = "users"

    sql_string = (
        f"INSERT INTO {table_name} ({', '.join(column_names)}) "
        f"VALUES ({', '.join(column_values)})"
    )
    statement = sqlparse.parse(sql_string)[0]

    table = insert.build_insert_table(statement)

    assert table.name == table_name

    query_column_names, query_column_values = zip(
        *[(col.name, col.value) for col in table.columns]
    )
    assert set(query_column_names) == {col.name for col in table.columns}
    assert list(query_column_names) == column_names
    assert list(query_column_values) == expected_values


@pytest.mark.parametrize(
    ["sql_string", "error_message"],
    [
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
def test_unsupported_build_insert_table(sql_string, error_message):
    statement = sqlparse.parse(sql_string)[0]

    with pytest.raises(exceptions.NotSupportedError, match=error_message):
        insert.build_insert_table(statement)
