# pylint: disable=missing-docstring,redefined-outer-name

from functools import reduce
import itertools

import pytest
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Float

from sqlalchemy_fauna import dialect
from sqlalchemy_fauna.fauna.translation import common


@pytest.fixture()
def user_model():
    table_name = "users"
    Base = declarative_base()

    class User(Base):  # pylint: disable=unused-variable
        __tablename__ = table_name

        id = Column(Integer, primary_key=True)
        name = Column(String, unique=True)
        date_joined = Column(DateTime, nullable=False)
        age = Column(Integer)
        finger_count = Column(Integer, default=10)
        is_premium_member = Column(Boolean, default=False)
        account_credit = Column(Float, default=0.0)
        job = Column(String)

    return User, Base


def test_has_table(user_model, fauna_engine):
    _, Base = user_model
    Base.metadata.create_all(fauna_engine)
    fauna_dialect = dialect.FaunaDialect()

    with fauna_engine.connect() as connection:
        assert fauna_dialect.has_table(connection, "users")
        assert not fauna_dialect.has_table(connection, "not_a_table")


def test_get_table_names(user_model, fauna_engine):
    _, Base = user_model
    Base.metadata.create_all(fauna_engine)
    fauna_dialect = dialect.FaunaDialect()

    with fauna_engine.connect() as connection:
        assert "users" in fauna_dialect.get_table_names(connection)


users_columns = [
    "id",
    "name",
    "date_joined",
    "age",
    "finger_count",
    "is_premium_member",
    "account_credit",
    "job",
]


def test_get_columns(user_model, fauna_engine):
    _, Base = user_model
    Base.metadata.create_all(fauna_engine)
    fauna_dialect = dialect.FaunaDialect()

    with fauna_engine.connect() as connection:
        queried_columns = fauna_dialect.get_columns(connection, "users")
        assert {column["name"] for column in queried_columns} == set(users_columns)


def test_get_indexes(user_model, fauna_engine):
    _, Base = user_model
    Base.metadata.create_all(fauna_engine)
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
                    for col in users_columns
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
        assert index_columns == set(users_columns)
