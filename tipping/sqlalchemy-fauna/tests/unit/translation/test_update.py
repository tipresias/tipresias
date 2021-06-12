# pylint: disable=missing-docstring,redefined-outer-name

import pytest
import sqlparse
from faunadb.objects import _Expr as QueryExpression

from sqlalchemy_fauna.fauna.translation import update


base_update = "UPDATE users SET users.name = 'Bob'"
update_where = base_update + " WHERE users.name = 'Teddy'"


@pytest.mark.parametrize("sql_query", [base_update, update_where])
def test_translate_update(sql_query):
    fql_query = update.translate_update(sqlparse.parse(sql_query)[0])

    assert isinstance(fql_query, QueryExpression)
