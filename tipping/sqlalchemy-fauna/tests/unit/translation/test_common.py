# pylint: disable=missing-docstring,redefined-outer-name

import pytest
from sqlparse import sql as token_groups
from sqlparse import tokens as token_types
from faker import Faker

from sqlalchemy_fauna.fauna.translation.common import extract_value


FAKE = Faker()

word = FAKE.word()
integer = FAKE.pyint()
float_number = FAKE.pyfloat()


@pytest.mark.parametrize(
    ["token_value", "expected"],
    [
        ("NONE", None),
        ("TRUE", True),
        ("FALSE", False),
        (word, word),
        (f"'{word}'", word),
        (f"'{word} ' {word}'", f"{word} ' {word}"),
        (integer, integer),
        (f"'{integer}'", str(integer)),
        (float_number, float_number),
        (f"'{float_number}'", str(float_number)),
    ],
)
def test_extract_value(token_value, expected):
    token = token_groups.Token(token_types.Literal, token_value)
    value = extract_value(token)
    assert value == expected
