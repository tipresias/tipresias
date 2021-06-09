# pylint: disable=missing-docstring,redefined-outer-name

import pytest
import sqlparse
from faunadb.objects import _Expr as QueryExpression

from sqlalchemy_fauna import exceptions
from sqlalchemy_fauna.fauna.translation import insert


insert_user = "INSERT INTO users (name, age, finger_count) VALUES ('Bob', 30, 10)"


@pytest.mark.parametrize("sql_query", [insert_user])
def test_translate_create(sql_query):
    fql_query = insert.translate_insert(sqlparse.parse(sql_query)[0])

    assert isinstance(fql_query, QueryExpression)


insert_all_cols = "INSERT INTO users VALUES ('Bob', 30, 10)"


@pytest.mark.parametrize(
    ["sql_query", "error_message"],
    [
        (
            insert_all_cols,
            "INSERT INTO statements without column names are not currently supported",
        )
    ],
)
def test_translating_unsupported_create(sql_query, error_message):
    with pytest.raises(exceptions.NotSupportedError, match=error_message):
        insert.translate_insert(sqlparse.parse(sql_query)[0])
