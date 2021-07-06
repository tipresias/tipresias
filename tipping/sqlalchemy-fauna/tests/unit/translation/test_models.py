# pylint: disable=missing-docstring,redefined-outer-name

import sqlparse
from sqlparse import sql as token_groups

from sqlalchemy_fauna.fauna.translation import models


def test_table_name():
    table_name = "users"
    sql_query = f"SELECT users.name FROM {table_name}"
    statement = sqlparse.parse(sql_query)[0]
    idx, _column_identifiers = statement.token_next_by(i=(token_groups.Identifier))
    _, table_identifier = statement.token_next_by(i=(token_groups.Identifier), idx=idx)

    table = models.Table(table_identifier)
    assert table.name == table_name
