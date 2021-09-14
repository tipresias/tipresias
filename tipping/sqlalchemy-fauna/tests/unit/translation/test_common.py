# pylint: disable=missing-docstring,redefined-outer-name

from datetime import timezone

import pytest
from sqlparse import sql as token_groups, tokens as token_types
from faker import Faker
from faunadb.objects import _Expr as QueryExpression
from faunadb import query as q

from sqlalchemy_fauna.fauna.translation import common

Fake = Faker()


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
