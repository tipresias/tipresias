# pylint: disable=missing-docstring,redefined-outer-name

import pytest
import sqlparse
from faunadb.objects import _Expr as QueryExpression

from sqlalchemy_fauna.fauna.translation import drop

drop_table = "DROP TABLE users"


@pytest.mark.parametrize("sql_query", [drop_table])
def test_translate_drop(sql_query):
    fql_query = drop.translate_drop(sqlparse.parse(sql_query)[0])

    assert isinstance(fql_query, QueryExpression)
