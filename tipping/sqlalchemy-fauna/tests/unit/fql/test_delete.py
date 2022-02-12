# pylint: disable=missing-docstring,redefined-outer-name

import pytest
from faunadb.objects import _Expr as QueryExpression

from tests.fixtures.factories import SQLQueryFactory
from sqlalchemy_fauna.fauna.fql import delete


@pytest.mark.parametrize(
    "sql_query",
    [SQLQueryFactory(table_count=1, filter_groups=[]), SQLQueryFactory(table_count=1)],
)
def test_translate_delete(sql_query):
    fql_query = delete.translate_delete(sql_query)

    assert isinstance(fql_query, QueryExpression)
