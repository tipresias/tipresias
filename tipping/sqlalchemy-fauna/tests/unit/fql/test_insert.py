# pylint: disable=missing-docstring,redefined-outer-name

import pytest
import sqlparse
from faunadb.objects import _Expr as QueryExpression

from tests.fixtures.factories import SQLQueryFactory
from sqlalchemy_fauna import sql
from sqlalchemy_fauna.fauna.fql import insert


@pytest.mark.parametrize("sql_query", [SQLQueryFactory(table_count=1)])
def test_translate_insert(sql_query):
    fql_query = insert.translate_insert(sql_query)

    assert isinstance(fql_query, QueryExpression)
