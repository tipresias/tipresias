# pylint: disable=missing-docstring,redefined-outer-name

from datetime import timezone

import pytest
from sqlparse import sql as token_groups
from sqlparse import tokens as token_types
from faker import Faker
import sqlparse

from sqlalchemy_fauna.fauna.translation.common import extract_value, parse_identifiers


FAKE = Faker()

word = FAKE.word()
integer = FAKE.pyint()
float_number = FAKE.pyfloat()
fake_datetime = FAKE.date_time_this_year(tzinfo=timezone.utc)
naive_datetime = FAKE.date_time_this_year()


@pytest.mark.parametrize(
    ["_label", "token_value", "expected"],
    [
        ("none", "NONE", None),
        ("true", "TRUE", True),
        ("false", "FALSE", False),
        ("string", word, word),
        ("quoted string", f"'{word}'", word),
        ("string with apostrophe", f"'{word} ' {word}'", f"{word} ' {word}"),
        ("int string", str(integer), integer),
        ("quoted int string", f"'{integer}'", str(integer)),
        ("float string", str(float_number), float_number),
        ("quoted float string", f"'{float_number}'", str(float_number)),
        ("iso datetime", fake_datetime.isoformat(), fake_datetime),
        ("string datetime", str(fake_datetime), fake_datetime),
        ("quoted iso datetime", f"'{fake_datetime.isoformat()}'", fake_datetime),
        (
            "naive datetime",
            naive_datetime.isoformat(),
            naive_datetime.replace(tzinfo=timezone.utc),
        ),
    ],
)
def test_extract_value(_label, token_value, expected):
    token = token_groups.Token(token_types.Literal, token_value)
    value = extract_value(token)
    assert value == expected


table_name = "users"
select_singl_column = f"SELECT users.id FROM {table_name}"
select_columns = f"SELECT users.id, users.name FROM {table_name}"
select_aliases = (
    f"SELECT users.id AS user_id, users.name AS user_name FROM {table_name}"
)


@pytest.mark.parametrize(
    ["sql_query", "expected_columns", "expected_aliases"],
    [
        (select_singl_column, ["id"], [None]),
        (select_columns, ["id", "name"], [None, None]),
        (select_aliases, ["id", "name"], ["user_id", "user_name"]),
    ],
)
def test_parse_identifiers(sql_query, expected_columns, expected_aliases):
    statement = sqlparse.parse(sql_query)[0]
    _, identifiers = statement.token_next_by(
        i=(token_groups.Identifier, token_groups.IdentifierList)
    )

    table_names, column_names, alias_names = parse_identifiers(identifiers)

    assert len(table_names) == len(column_names) == len(alias_names)

    for table in table_names:
        assert table == table_name

    for column, expected_column in zip(column_names, expected_columns):
        assert column == expected_column

    for alias, expected_alias in zip(alias_names, expected_aliases):
        assert alias == expected_alias
