# pylint: disable=missing-docstring,redefined-outer-name

import pytest
import sqlparse
from faunadb.objects import _Expr as QueryExpression

from sqlalchemy_fauna import sql
from sqlalchemy_fauna.fauna.fql import insert


@pytest.mark.parametrize(
    "sql_string", ["INSERT INTO users (name, age, finger_count) VALUES ('Bob', 30, 10)"]
)
def test_translate_insert(sql_string):
    sql_statement = sqlparse.parse(sql_string)[0]
    sql_query = sql.SQLQuery.from_statement(sql_statement)

    fql_query = insert.translate_insert(sql_query)

    assert isinstance(fql_query, QueryExpression)
