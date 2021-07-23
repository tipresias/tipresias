# pylint: disable=missing-docstring,redefined-outer-name

from datetime import timezone

import pytest
from sqlparse import sql as token_groups
from sqlparse import tokens as token_types
from faker import Faker
import sqlparse
from faunadb.objects import _Expr as QueryExpression
from faunadb import query as q

from sqlalchemy_fauna import exceptions
from sqlalchemy_fauna.fauna.translation import common, models

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


select_values = "SELECT * FROM users"
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
        (where_in, "Only single, literal values are permitted"),
        (where_or, "OR not yet supported in WHERE clauses."),
    ],
)
def test_parsing_unsupported_where(sql_query, error_message):
    statement = sqlparse.parse(sql_query)[0]
    idx, _ = statement.token_next_by(m=(token_types.Keyword, "FROM"))
    _, table_identifier = statement.token_next_by(i=(token_groups.Identifier), idx=idx)
    table = models.Table.from_identifier(table_identifier)
    _, where_group = statement.token_next_by(i=(token_groups.Where))

    with pytest.raises(exceptions.NotSupportedError, match=error_message):
        common.parse_where(where_group, table)


where_id = select_values + f" WHERE users.id = '{FAKE.credit_card_number}'"
where_equals = select_values + f" WHERE users.name = '{FAKE.first_name()}'"
where_and = (
    where_equals
    + f" AND users.age = {FAKE.pyint()} AND users.finger_count = {FAKE.pyint()}"
)
where_greater = select_values + f" WHERE users.age > {FAKE.pyint()}"
where_greater_equal = select_values + f" WHERE users.age >= {FAKE.pyint()}"
where_less = select_values + f" WHERE users.age < {FAKE.pyint()}"
where_less_equal = select_values + f" WHERE users.age <= {FAKE.pyint()}"
where_is_null = select_values + " WHERE users.job IS NULL"


@pytest.mark.parametrize(
    "sql_query",
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
    ],
)
def test_parsing_where(sql_query):
    statement = sqlparse.parse(sql_query)[0]
    idx, _ = statement.token_next_by(m=(token_types.Keyword, "FROM"))
    _, table_identifier = statement.token_next_by(i=(token_groups.Identifier), idx=idx)
    table = models.Table.from_identifier(table_identifier)
    _, where_group = statement.token_next_by(i=(token_groups.Where))

    fql_query = common.parse_where(where_group, table)
    assert isinstance(fql_query, QueryExpression)


def test_get_foreign_key_ref():
    fql_query = q.let(
        {"references": {}, "foreign_key": FAKE.credit_card_number()},
        common.get_foreign_key_ref(q.var("foreign_key"), q.var("references")),
    )

    assert isinstance(fql_query, QueryExpression)
