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


def test_get_foreign_key_ref():
    fql_query = q.let(
        {"references": {}, "foreign_key": FAKE.credit_card_number()},
        common.get_foreign_key_ref(q.var("foreign_key"), q.var("references")),
    )

    assert isinstance(fql_query, QueryExpression)
