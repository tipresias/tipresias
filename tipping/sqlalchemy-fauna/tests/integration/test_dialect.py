# pylint: disable=missing-docstring,redefined-outer-name

from functools import reduce
import itertools

from sqlalchemy_fauna import dialect
from sqlalchemy_fauna.fauna.translation import common


def test_has_table(fauna_engine):
    fauna_dialect = dialect.FaunaDialect()

    with fauna_engine.connect() as connection:
        assert fauna_dialect.has_table(connection, "users")
        assert not fauna_dialect.has_table(connection, "not_a_table")


def test_get_table_names(fauna_engine):
    fauna_dialect = dialect.FaunaDialect()

    with fauna_engine.connect() as connection:
        assert "users" in fauna_dialect.get_table_names(connection)


def test_get_columns(fauna_engine, user_columns):
    fauna_dialect = dialect.FaunaDialect()

    with fauna_engine.connect() as connection:
        queried_columns = fauna_dialect.get_columns(connection, "users")
        assert {column["name"] for column in queried_columns} == set(user_columns)


def test_get_indexes(fauna_engine, user_columns):
    fauna_dialect = dialect.FaunaDialect()

    with fauna_engine.connect() as connection:
        queried_indexes = fauna_dialect.get_indexes(connection, "users")
        index_names = {index["name"] for index in queried_indexes}
        expected_value_indices = list(
            itertools.chain.from_iterable(
                [
                    [
                        common.index_name("users", col, common.IndexType.VALUE),
                        common.index_name("users", col, common.IndexType.SORT),
                    ]
                    for col in user_columns
                    if col != "id"
                ]
            )
        )
        expected_misc_indices = ["users_all", "users_ref", "users_by_name_term"]
        expected_indices = expected_value_indices + expected_misc_indices

        assert index_names == set(expected_indices)

        index_columns = reduce(
            lambda acc, curr: set(curr["column_names"]) | acc, queried_indexes, set([])
        )
        assert index_columns == set(user_columns)


def test_get_pk_constraint(fauna_engine):
    fauna_dialect = dialect.FaunaDialect()

    with fauna_engine.connect() as connection:
        pk_constraint = fauna_dialect.get_pk_constraint(connection, "users")

    assert pk_constraint == {"constrained_columns": ["id"], "name": "PRIMARY KEY"}


def test_get_unique_constraints(fauna_engine):
    fauna_dialect = dialect.FaunaDialect()

    with fauna_engine.connect() as connection:
        unique_constraints = fauna_dialect.get_unique_constraints(connection, "users")

    for constraint in unique_constraints:
        assert constraint == {
            "name": "UNIQUE",
            "column_names": ["name"],
            "duplicates_index": "users_by_name_term",
        }
