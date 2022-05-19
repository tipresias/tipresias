# pylint: disable=missing-docstring,redefined-outer-name

from faunadb.objects import _Expr as QueryExpression

from tests.fixtures.factories import TableFactory
from sqlalchemy_fauna.fauna.fql import insert


def test_translate_insert():
    fql_query = insert.translate_insert(TableFactory())

    assert isinstance(fql_query, QueryExpression)
