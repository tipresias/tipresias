# pylint: disable=missing-docstring,redefined-outer-name

import pytest
import sqlparse
from faunadb.objects import _Expr as QueryExpression

from sqlalchemy_fauna.fauna.translation import delete


base_delete = "DELETE FROM users"
delete_where = base_delete + " WHERE users.name = 'Bob'"


@pytest.mark.parametrize("sql_query", [base_delete, delete_where])
def test_translate_delete(sql_query):
    fql_queries = delete.translate_delete(sqlparse.parse(sql_query)[0])

    for fql_query in fql_queries:
        assert isinstance(fql_query, QueryExpression)
