# pylint: disable=missing-docstring,redefined-outer-name

import pytest
import sqlparse
from faunadb.objects import _Expr as QueryExpression

from sqlalchemy_fauna import exceptions
from sqlalchemy_fauna.fauna.translation import alter


alter_table = "ALTER TABLE users"
alter_column = f"{alter_table} ALTER COLUMN age"
drop_default = f"{alter_column} DROP DEFAULT"


@pytest.mark.parametrize("sql_query", [drop_default])
def test_translate_alter(sql_query):
    fql_queries = alter.translate_alter(sqlparse.parse(sql_query)[0])

    for fql_query in fql_queries:
        assert isinstance(fql_query, QueryExpression)


rename_table = f"{alter_table} RENAME TO people"
rename_column = f"{alter_table} RENAME COLUMN age TO years_on_earth"
add_column = f"{alter_table} ADD COLUMN height INT"
drop_column = f"{alter_table} DROP COLUMN height"
set_default = f"{alter_column} SET DEFAULT 10"
change_data_type = f"{alter_column} TYPE FLOAT"


@pytest.mark.parametrize(
    ["sql_query", "error_message"],
    [
        (rename_table, "only ALTER COLUMN is currently supported"),
        (rename_column, "only ALTER COLUMN is currently supported"),
        (add_column, "only ALTER COLUMN is currently supported"),
        (drop_column, "only ALTER COLUMN is currently supported"),
        (set_default, "only DROP DEFAULT is currently supported"),
        (change_data_type, "only DROP DEFAULT is currently supported"),
    ],
)
def test_translating_unsupported_alter(sql_query, error_message):
    with pytest.raises(exceptions.NotSupportedError, match=error_message):
        alter.translate_alter(sqlparse.parse(sql_query)[0])
