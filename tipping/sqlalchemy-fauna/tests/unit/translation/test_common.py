# pylint: disable=missing-docstring,redefined-outer-name

from datetime import timezone

import pytest
from sqlparse import sql as token_groups, tokens as token_types
from faker import Faker
from faunadb.objects import _Expr as QueryExpression
from faunadb import query as q

from sqlalchemy_fauna.fauna.translation import common

Fake = Faker()

word = Fake.word()
integer = Fake.pyint()
float_number = Fake.pyfloat()
fake_datetime = Fake.date_time_this_year(tzinfo=timezone.utc)
naive_datetime = Fake.date_time_this_year()


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
        {"references": {}, "foreign_key": Fake.credit_card_number()},
        common.get_foreign_key_ref(q.var("foreign_key"), q.var("references")),
    )

    assert isinstance(fql_query, QueryExpression)


@pytest.mark.parametrize(
    ["params", "expected_name"],
    [
        (("users",), "users_all"),
        (("users", None, common.IndexType.REF), "users_ref"),
        (("users", "name", common.IndexType.TERM), "users_by_name_term"),
        (("users", "name", common.IndexType.REF, "age"), "users_by_name_ref_to_age"),
    ],
)
def test_index_name(params, expected_name):
    assert common.index_name(*params) == expected_name


@pytest.mark.parametrize(
    "params",
    [
        ("users", "name"),
        ("users", None, common.IndexType.VALUE),
        ("users", None, common.IndexType.REF, "age"),
        ("users", "name", common.IndexType.VALUE, "age"),
    ],
)
def test_invalid_index_name(params):
    with pytest.raises(AssertionError):
        common.index_name(*params)
