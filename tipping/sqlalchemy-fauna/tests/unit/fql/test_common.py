# pylint: disable=missing-docstring,redefined-outer-name

import pytest
from faker import Faker
from faunadb.objects import _Expr as QueryExpression
from faunadb import query as q
import numpy as np
import sqlparse

from sqlalchemy_fauna import exceptions, sql
from sqlalchemy_fauna.sql.sql_table import SetOperation
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
    "filter_params",
    [{"operator": "LIKE"}],
)
def test_unsupported_build_document_set_intersection(filter_params):
    table_name = Fake.word()
    column_params = {
        "name": Fake.word(),
        "alias": Fake.word(),
        "table_name": table_name,
        "position": 0,
    }
    column = sql.Column(**column_params)

    base_filter_params = {
        "column": column,
        "operator": np.random.choice(sql.Filter.SUPPORTED_COMPARISON_OPERATORS),
        "value": Fake.word(),
    }
    filter_params = {**base_filter_params, **filter_params}
    query_filter = sql.Filter(**filter_params)

    table = sql.Table(name=table_name, columns=[column], filters=[query_filter])
    filter_group = sql.FilterGroup(
        set_operation=SetOperation.INTERSECTION, filters=[query_filter]
    )

    with pytest.raises(exceptions.NotSupportedError, match="Unsupported operator"):
        common.build_document_set_intersection(table, filter_group)


@pytest.mark.parametrize(
    ["filter_params", "column_params"],
    [
        ({"operator": "=", "value": Fake.uuid4()}, {"name": "ref", "alias": "id"}),
        ({"operator": "="}, {}),
        ({"operator": ">=", "value": Fake.pyint()}, {}),
        ({"operator": ">", "value": Fake.pyint()}, {}),
        ({"operator": "<=", "value": Fake.pyint()}, {}),
        ({"operator": "<", "value": Fake.pyint()}, {}),
    ],
)
def test_build_document_set_intersection(filter_params, column_params):
    table_name = Fake.word()
    base_column_params = {
        "name": Fake.word(),
        "alias": Fake.word(),
        "table_name": table_name,
        "position": 0,
    }
    column = sql.Column(**{**base_column_params, **column_params})

    base_filter_params = {
        "column": column,
        "operator": np.random.choice(sql.Filter.SUPPORTED_COMPARISON_OPERATORS),
        "value": Fake.word(),
    }
    query_filter = sql.Filter(**{**base_filter_params, **filter_params})

    table = sql.Table(name=table_name, columns=[column], filters=[query_filter])
    filter_group = sql.FilterGroup(
        set_operation=SetOperation.INTERSECTION, filters=[query_filter]
    )

    fql_query = common.build_document_set_intersection(table, filter_group)
    assert isinstance(fql_query, QueryExpression)


def test_join_collections():
    from_table = "users"
    first_child_table = "accounts"

    select_string = f"SELECT {from_table}.name, {from_table}.age "
    from_string = f"FROM {from_table} "
    join_string = (
        f"JOIN {first_child_table} ON {from_table}.id = {first_child_table}.user_id "
    )
    where_string = f"WHERE {first_child_table}.amount > 5.0"
    sql_string = select_string + from_string + join_string + where_string

    sql_statement = sqlparse.parse(sql_string)[0]
    sql_query = sql.SQLQuery.from_statement(sql_statement)

    join_query = common.join_collections(sql_query)
    assert isinstance(join_query, QueryExpression)

    second_child_table = "transactions"
    join_string = (
        join_string
        + f"JOIN {second_child_table} ON {first_child_table}.id = {second_child_table}.account_id "
    )
    where_string = where_string + f" AND {second_child_table}.count < 10"
    sql_string = select_string + from_string + join_string + where_string

    sql_statement = sqlparse.parse(sql_string)[0]
    sql_query = sql.SQLQuery.from_statement(sql_statement)

    join_query = common.join_collections(sql_query)
    assert isinstance(join_query, QueryExpression)

    first_parent_table = "banks"
    join_string = (
        join_string
        + f"JOIN {first_parent_table} ON {first_parent_table}.id = {second_child_table}.bank_id "
    )
    where_string = where_string + f" OR {first_parent_table}.id = 'asdf1234'"
    sql_string = select_string + from_string + join_string + where_string

    sql_statement = sqlparse.parse(sql_string)[0]
    sql_query = sql.SQLQuery.from_statement(sql_statement)

    join_query = common.join_collections(sql_query)
    assert isinstance(join_query, QueryExpression)

    second_parent_table = "country"
    join_string = (
        join_string + f"JOIN {second_parent_table} "
        f"ON {first_parent_table}.id = {second_parent_table}.country_id "
    )
    where_string = where_string + f" AND {second_parent_table}.code = 'AU'"
    sql_string = select_string + from_string + join_string + where_string

    sql_statement = sqlparse.parse(sql_string)[0]
    sql_query = sql.SQLQuery.from_statement(sql_statement)

    join_query = common.join_collections(sql_query)
    assert isinstance(join_query, QueryExpression)


@pytest.mark.parametrize(
    ["sql_string", "error_message"],
    [
        (
            "SELECT users.name, users.age FROM users",
            "Joining tables without cross-table filters via the WHERE clause is not supported",
        ),
        (
            "SELECT users.name, users.age FROM users JOIN transactions "
            "ON users.id = transactions.user_id ORDER BY transactions.id",
            "we currently can only sort the principal table",
        ),
    ],
)
def test_invalid_join_collections(sql_string, error_message):
    sql_statement = sqlparse.parse(sql_string)[0]
    sql_query = sql.SQLQuery.from_statement(sql_statement)

    with pytest.raises(exceptions.NotSupportedError, match=error_message):
        common.join_collections(sql_query)


def test_update_documents():
    table_name = Fake.first_name()
    sql_string = (
        f"UPDATE {table_name} "
        f"SET {Fake.first_name()} = '{Fake.first_name()}', "
        f"{Fake.first_name()} = '{Fake.first_name()}', "
        f"{Fake.first_name()} = {Fake.pyint()}, "
    )
    sql_statement = sqlparse.parse(sql_string)[0]
    sql_query = sql.SQLQuery.from_statement(sql_statement)

    update_query = common.update_documents(sql_query)

    assert isinstance(update_query, QueryExpression)


@pytest.mark.parametrize(
    "sql_string",
    [
        (
            "SELECT users.name, users.age FROM users "
            "WHERE users.name = 'Bob' "
            "AND users.age > 30 "
            "OR users.job = 'cook'"
        ),
        "SELECT users.name, users.age FROM users",
    ],
)
def test_build_document_set_union(sql_string):
    sql_statement = sqlparse.parse(sql_string)[0]
    sql_query = sql.SQLQuery.from_statement(sql_statement)

    set_union = common.build_document_set_union(
        sql_query.tables[0], sql_query.filter_group.filters
    )

    assert isinstance(set_union, QueryExpression)
