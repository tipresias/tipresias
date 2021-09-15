# pylint: disable=missing-docstring,redefined-outer-name

from datetime import timezone

from sqlparse import sql as token_groups, tokens as token_types
import pytest
from faker import Faker

from sqlalchemy_fauna.sql import common


Fake = Faker()
column_name = "name"

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
