# pylint: disable=missing-docstring,redefined-outer-name

import pytest
from faker import Faker
from faunadb.objects import _Expr as QueryExpression
from faunadb import query as q

from tests.fixtures.factories import (
    ColumnFactory,
    FilterGroupFactory,
    FilterFactory,
    TableFactory,
    SQLQueryFactory,
    OrderByFactory,
)
from sqlalchemy_fauna import exceptions, sql
from sqlalchemy_fauna.fauna.fql import common


Fake = Faker()


def test_get_foreign_key_ref():
    fql_query = q.let(
        {"references": {}, "foreign_key": Fake.credit_card_number()},
        common.get_foreign_key_ref(q.var("foreign_key"), q.var("references")),
    )

    assert isinstance(fql_query, QueryExpression)


@pytest.mark.parametrize(
    ["params", "expected_name"],
    [
        (("users",), "users_all"),
        (("users", None, common.IndexType.REF), "users_ref"),
        (("users", "name", common.IndexType.TERM), "users_by_name_term"),
        (("users", "name", common.IndexType.REF, "age"), "users_by_name_ref_to_age"),
    ],
)
def test_index_name(params, expected_name):
    assert common.index_name(*params) == expected_name


@pytest.mark.parametrize(
    ["table_name", "kwargs"],
    [
        ("users", {"column_name": "name"}),
        ("users", {"index_type": common.IndexType.VALUE}),
        ("users", {"index_type": common.IndexType.VALUE, "foreign_key_name": "age"}),
        (
            "users",
            {
                "column_name": "name",
                "index_type": common.IndexType.VALUE,
                "foreign_key_name": "age",
            },
        ),
    ],
)
def test_invalid_index_name(table_name, kwargs):
    with pytest.raises(AssertionError):
        common.index_name(table_name, **kwargs)


select_values = "SELECT * FROM users"
where_not_equal_1 = select_values + f" WHERE users.age <> {Fake.pyint()}"
where_not_equal_2 = select_values + f" WHERE users.age != {Fake.pyint()}"
where_between = (
    select_values + f" WHERE users.age BETWEEN {Fake.pyint()} AND {Fake.pyint}"
)
where_like = select_values + f" WHERE users.name LIKE '%{Fake.first_name()}%'"
where_in = (
    select_values
    + f" WHERE users.name IN ('{Fake.first_name()}', '{Fake.first_name()}')"
)
where_or = (
    select_values
    + f" WHERE users.name = '{Fake.first_name()}' OR users.age = {Fake.pyint()}"
)


@pytest.mark.parametrize(
    ["operator", "column_params"],
    [
        (
            sql.sql_table.ComparisonOperator.EQUAL,
            {"name": "ref", "alias": "id"},
        ),
        (
            sql.sql_table.ComparisonOperator.EQUAL,
            {},
        ),
        (
            sql.sql_table.ComparisonOperator.GREATER_THAN_OR_EQUAL,
            {},
        ),
        (
            sql.sql_table.ComparisonOperator.GREATER_THAN,
            {},
        ),
        (
            sql.sql_table.ComparisonOperator.LESS_THAN_OR_EQUAL,
            {},
        ),
        (
            sql.sql_table.ComparisonOperator.LESS_THAN,
            {},
        ),
    ],
)
def test_build_document_set_intersection(operator, column_params):
    column = ColumnFactory(**column_params)
    filter_group = FilterGroupFactory(
        filters=[FilterFactory(column=column, comparison__operator=operator)]
    )

    table = TableFactory(
        name=column.table_name, columns=[column], filters=filter_group.filters
    )

    fql_query = common.build_document_set_intersection(table, filter_group)
    assert isinstance(fql_query, QueryExpression)


def test_join_collections():
    ENOUGH_TO_PROBABLY_GET_A_VARIETY_OF_JOINS = 6
    query = SQLQueryFactory(table_count=ENOUGH_TO_PROBABLY_GET_A_VARIETY_OF_JOINS)

    join_query = common.join_collections(query)
    assert isinstance(join_query, QueryExpression)


@pytest.mark.parametrize(
    ["sql_query", "error_message"],
    [
        (
            SQLQueryFactory(table_count=1, filter_groups=[]),
            "Joining tables without cross-table filters via the WHERE clause is not supported",
        ),
        (
            SQLQueryFactory(order_by=OrderByFactory()),
            "we currently can only sort the principal table",
        ),
    ],
)
def test_invalid_join_collections(sql_query, error_message):
    with pytest.raises(exceptions.NotSupportedError, match=error_message):
        common.join_collections(sql_query)


def test_update_documents():
    update_query = common.update_documents(SQLQueryFactory(table_count=1))

    assert isinstance(update_query, QueryExpression)


@pytest.mark.parametrize(
    "sql_query",
    [
        SQLQueryFactory(table_count=1),
        SQLQueryFactory(table_count=1, filter_groups=[]),
    ],
)
def test_build_document_set_union(sql_query):
    set_union = common.build_document_set_union(
        sql_query.tables[0], sql_query.filter_groups
    )

    assert isinstance(set_union, QueryExpression)
