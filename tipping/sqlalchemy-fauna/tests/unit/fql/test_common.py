# pylint: disable=missing-docstring,redefined-outer-name

import pytest
from faker import Faker
from faunadb.objects import _Expr as QueryExpression
from faunadb import query as q
import numpy as np

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
    "params",
    [
        ("users", "name"),
        ("users", None, common.IndexType.VALUE),
        ("users", None, common.IndexType.REF, "age"),
        ("users", "name", common.IndexType.VALUE, "age"),
    ],
)
def test_invalid_index_name(params):
    with pytest.raises(AssertionError):
        common.index_name(*params)


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
def test_unsupported_define_document_set(filter_params):
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

    with pytest.raises(exceptions.NotSupportedError, match="Unsupported operator"):
        common.define_document_set(table)


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
def test_define_document_set(filter_params, column_params):
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

    fql_query = common.define_document_set(table)
    assert isinstance(fql_query, QueryExpression)


def test_join_collections():
    from_table = sql.Table(name=Fake.word())

    first_child_table = sql.Table(name=Fake.word())
    from_table.right_join_table = first_child_table
    from_table.right_join_key = sql.Column(
        name="ref", table_name=from_table.name, alias=Fake.word(), position=0
    )
    first_child_table.left_join_table = from_table
    first_child_table.left_join_key = sql.Column(
        name=Fake.word(),
        table_name=first_child_table.name,
        alias=Fake.word(),
        position=1,
    )

    join_query = common.join_collections(from_table)
    assert isinstance(join_query, QueryExpression)

    second_child_table = sql.Table(name=Fake.word())
    first_child_table.right_join_table = second_child_table
    first_child_table.right_join_key = sql.Column(
        name="ref", table_name=first_child_table.name, alias=Fake.word(), position=2
    )
    second_child_table.left_join_table = first_child_table
    second_child_table.left_join_key = sql.Column(
        name=Fake.word(),
        table_name=second_child_table.name,
        alias=Fake.word(),
        position=3,
    )

    join_query = common.join_collections(from_table)
    assert isinstance(join_query, QueryExpression)

    first_parent_table = sql.Table(name=Fake.word())
    second_child_table.right_join_table = first_parent_table
    second_child_table.right_join_key = sql.Column(
        name=Fake.word(),
        table_name=second_child_table.name,
        alias=Fake.word(),
        position=4,
    )
    first_parent_table.left_join_table = second_child_table
    first_parent_table.left_join_key = sql.Column(
        name="ref", table_name=first_parent_table.name, alias=Fake.word(), position=5
    )

    join_query = common.join_collections(from_table)
    assert isinstance(join_query, QueryExpression)

    second_parent_table = sql.Table(name=Fake.word())
    first_parent_table.right_join_table = second_parent_table
    first_parent_table.right_join_key = sql.Column(
        name=Fake.word(),
        table_name=first_parent_table.name,
        alias=Fake.word(),
        position=6,
    )
    second_parent_table.left_join_table = first_parent_table
    second_parent_table.left_join_key = sql.Column(
        name="ref", table_name=second_parent_table.name, alias=Fake.word(), position=7
    )

    join_query = common.join_collections(from_table)
    assert isinstance(join_query, QueryExpression)


def test_invalid_join_collections():
    from_table = sql.Table(name=Fake.word())
    with pytest.raises(AssertionError):
        common.join_collections(from_table)

    further_left_table = sql.Table(name=Fake.word())
    from_table.left_join_table = further_left_table
    from_table.left_join_key = sql.Column(
        name=Fake.word(),
        table_name=further_left_table.name,
        alias=Fake.word(),
        position=0,
    )
    with pytest.raises(AssertionError):
        common.join_collections(from_table)


def test_update_documents():
    table_name = Fake.first_name()
    columns = [
        sql.Column(
            name=Fake.first_name(),
            alias=Fake.first_name(),
            table_name=table_name,
            position=1,
        )
        for _ in range(3)
    ]
    table = sql.Table(name=table_name, columns=columns)

    update_query = common.update_documents(table)

    assert isinstance(update_query, QueryExpression)
