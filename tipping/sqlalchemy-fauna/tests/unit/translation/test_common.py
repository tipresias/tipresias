# pylint: disable=missing-docstring,redefined-outer-name

from datetime import timezone

import pytest
from sqlparse import sql as token_groups
from sqlparse import tokens as token_types
from faker import Faker
import sqlparse
from faunadb.objects import _Expr as QueryExpression

from sqlalchemy_fauna import exceptions
from sqlalchemy_fauna.fauna.translation import common

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
    value = common.extract_value(token)
    assert value == expected


table_name = "users"
select_singl_column = f"SELECT {table_name}.id FROM {table_name}"
select_columns = f"SELECT {table_name}.id, {table_name}.name FROM {table_name}"
select_aliases = (
    f"SELECT {table_name}.id AS user_id, {table_name}.name AS user_name "
    "FROM {table_name}"
)
select_function = f"SELECT count({table_name}.id) FROM {table_name}"
select_function_alias = (
    f"SELECT count({table_name}.id) AS count_{table_name} FROM {table_name}"
)


@pytest.mark.parametrize(
    ["sql_query", "expected_columns", "expected_aliases"],
    [
        (select_singl_column, ["ref"], ["id"]),
        (select_columns, ["ref", "name"], ["id", "name"]),
        (select_aliases, ["ref", "name"], ["user_id", "user_name"]),
        (select_function, [f"count({table_name}.id)"], [f"count({table_name}.id)"]),
        (select_function_alias, [f"count({table_name}.id)"], [f"count_{table_name}"]),
    ],
)
def test_parse_identifiers(sql_query, expected_columns, expected_aliases):
    statement = sqlparse.parse(sql_query)[0]
    _, identifiers = statement.token_next_by(
        i=(token_groups.Identifier, token_groups.IdentifierList, token_groups.Function)
    )

    table_field_map = common.parse_identifiers(identifiers, table_name)

    for table in table_field_map.keys():
        assert table == table_name

    for column in table_field_map[table_name]:
        assert column in expected_columns

    for alias in table_field_map[table_name].values():
        assert alias in expected_aliases


select_values = "SELECT * FROM users"
where_greater = select_values + f" WHERE users.age > {FAKE.pyint()}"
where_greater_equal = select_values + f" WHERE users.age >= {FAKE.pyint()}"
where_less = select_values + f" WHERE users.age < {FAKE.pyint()}"
where_less_equal = select_values + f" WHERE users.age <= {FAKE.pyint()}"
where_not_equal_1 = select_values + f" WHERE users.age <> {FAKE.pyint()}"
where_not_equal_2 = select_values + f" WHERE users.age != {FAKE.pyint()}"
where_between = (
    select_values + f" WHERE users.age BETWEEN {FAKE.pyint()} AND {FAKE.pyint}"
)
where_like = select_values + f" WHERE users.name LIKE '%{FAKE.first_name()}%'"
where_in = (
    select_values
    + f" WHERE users.name IN ('{FAKE.first_name()}', '{FAKE.first_name()}')"
)
where_or = (
    select_values
    + f" WHERE users.name = '{FAKE.first_name()}' OR users.age = {FAKE.pyint()}"
)


@pytest.mark.parametrize(
    ["sql_query", "error_message"],
    [
        (
            where_greater,
            "Only column-value equality conditions are currently supported",
        ),
        (
            where_greater_equal,
            "Only column-value equality conditions are currently supported",
        ),
        (
            where_less,
            "Only column-value equality conditions are currently supported",
        ),
        (
            where_less_equal,
            "Only column-value equality conditions are currently supported",
        ),
        (
            where_not_equal_1,
            "Only column-value equality conditions are currently supported",
        ),
        (
            where_not_equal_2,
            "Only column-value equality conditions are currently supported",
        ),
        (
            where_between,
            "BETWEEN not yet supported in WHERE clauses",
        ),
        (
            where_like,
            "Only column-value equality conditions are currently supported",
        ),
        (
            where_in,
            "Only column-value equality conditions are currently supported",
        ),
        (where_or, "OR not yet supported in WHERE clauses."),
    ],
)
def test_parsing_unsupported_where(sql_query, error_message):
    statement = sqlparse.parse(sql_query)[0]
    _, where_group = statement.token_next_by(i=(token_groups.Where))

    with pytest.raises(exceptions.NotSupportedError, match=error_message):
        common.parse_where(where_group, "users")


where_id = select_values + f" WHERE users.id = '{FAKE.credit_card_number}'"
where_equals = select_values + f" WHERE users.name = '{FAKE.first_name()}'"
where_and = (
    where_equals
    + f" AND users.age = {FAKE.pyint()} AND users.finger_count = {FAKE.pyint()}"
)


@pytest.mark.parametrize(
    "sql_query",
    [select_values, where_id, where_equals, where_and],
)
def test_translate_select(sql_query):
    statement = sqlparse.parse(sql_query)[0]
    _, where_group = statement.token_next_by(i=(token_groups.Where))

    fql_query = common.parse_where(where_group, "users")
    assert isinstance(fql_query, QueryExpression)
