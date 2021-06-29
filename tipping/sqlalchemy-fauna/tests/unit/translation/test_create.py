# pylint: disable=missing-docstring,redefined-outer-name

import pytest
import sqlparse
from faunadb.objects import _Expr as QueryExpression

from sqlalchemy_fauna.fauna.translation import create
from sqlalchemy_fauna import exceptions

create_table = (
    "CREATE TABLE users (id INTEGER NOT NULL, "
    "name VARCHAR, date_joined DATETIME NOT NULL, "
    "age INTEGER, finger_count INTEGER, PRIMARY KEY (id), UNIQUE (name))"
)
create_index = "CREATE INDEX ix_users_name ON users (name)"


@pytest.mark.parametrize("sql_query", [create_table, create_index])
def test_translate_create(sql_query):
    fql_queries = create.translate_create(sqlparse.parse(sql_query)[0])

    for fql_query in fql_queries:
        assert isinstance(fql_query, QueryExpression)


create_check = "CREATE TABLE users (id INTEGER NOT NULL, age INTEGER CHECK (age > 40))"
multiple_references = (
    "CREATE TABLE users (id INTEGER NOT NULL, account_id INTEGER NOT NULL, "
    "PRIMARY KEY (id), FOREIGN KEY(account_id) REFERENCES bank_accounts (id), "
    "FOREIGN KEY(account_id) REFERENCES social_accounts (id))"
)
non_id_reference = (
    "CREATE TABLE users (id INTEGER NOT NULL, account_name VARCHAR NOT NULL, "
    "PRIMARY KEY (id), FOREIGN KEY(account_name) REFERENCES accounts (name))"
)


@pytest.mark.parametrize(
    ["sql_query", "error_message"],
    [
        (create_check, "CHECK keyword is not supported"),
        (multiple_references, "Foreign keys with multiple references"),
        (non_id_reference, "Foreign keys referring to fields other than ID"),
    ],
)
def test_translating_unsupported_create(sql_query, error_message):
    with pytest.raises(exceptions.NotSupportedError, match=error_message):
        create.translate_create(sqlparse.parse(sql_query)[0])
