# pylint: disable=missing-docstring,redefined-outer-name

import pytest
import sqlparse
from faunadb.objects import _Expr as QueryExpression

from sqlalchemy_fauna import sql
from sqlalchemy_fauna.fauna.fql import delete


base_delete = "DELETE FROM users"
delete_where = base_delete + " WHERE users.name = 'Bob'"


@pytest.mark.parametrize("sql_string", [base_delete, delete_where])
def test_translate_delete(sql_string):
    statement = sqlparse.parse(sql_string)[0]
    sql_query = sql.SQLQuery.from_statement(statement)
    fql_query = delete.translate_delete(sql_query)

    assert isinstance(fql_query, QueryExpression)
