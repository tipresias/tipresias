# pylint: disable=missing-docstring,redefined-outer-name

from faker import Faker
import pytest
from faunadb.objects import _Expr as QueryExpression
import numpy as np

from sqlalchemy_fauna import exceptions
from sqlalchemy_fauna.fauna.translation import fql, models

Fake = Faker()

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
    }
    column = models.Column(**column_params)

    base_filter_params = {
        "column": column,
        "operator": np.random.choice(models.Filter.SUPPORTED_COMPARISON_OPERATORS),
        "value": Fake.word(),
    }
    filter_params = {**base_filter_params, **filter_params}
    query_filter = models.Filter(**filter_params)

    table = models.Table(name=table_name, columns=[column], filters=[query_filter])

    with pytest.raises(exceptions.NotSupportedError, match="Unsupported operator"):
        fql.define_document_set(table)


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
    }
    column = models.Column(**{**base_column_params, **column_params})

    base_filter_params = {
        "column": column,
        "operator": np.random.choice(models.Filter.SUPPORTED_COMPARISON_OPERATORS),
        "value": Fake.word(),
    }
    query_filter = models.Filter(**{**base_filter_params, **filter_params})

    table = models.Table(name=table_name, columns=[column], filters=[query_filter])

    fql_query = fql.define_document_set(table)
    assert isinstance(fql_query, QueryExpression)


def test_join_collections():
    from_table = models.Table(name=Fake.word())

    first_child_table = models.Table(name=Fake.word())
    from_table.right_join_table = first_child_table
    from_table.right_join_key = models.Column(
        name="ref", table_name=from_table.name, alias=Fake.word()
    )
    first_child_table.left_join_table = from_table
    first_child_table.left_join_key = models.Column(
        name=Fake.word(), table_name=first_child_table.name, alias=Fake.word()
    )

    join_query = fql.join_collections(from_table)
    assert isinstance(join_query, QueryExpression)

    second_child_table = models.Table(name=Fake.word())
    first_child_table.right_join_table = second_child_table
    first_child_table.right_join_key = models.Column(
        name="ref", table_name=first_child_table.name, alias=Fake.word()
    )
    second_child_table.left_join_table = first_child_table
    second_child_table.left_join_key = models.Column(
        name=Fake.word(), table_name=second_child_table.name, alias=Fake.word()
    )

    join_query = fql.join_collections(from_table)
    assert isinstance(join_query, QueryExpression)

    first_parent_table = models.Table(name=Fake.word())
    second_child_table.right_join_table = first_parent_table
    second_child_table.right_join_key = models.Column(
        name=Fake.word(), table_name=second_child_table.name, alias=Fake.word()
    )
    first_parent_table.left_join_table = second_child_table
    first_parent_table.left_join_key = models.Column(
        name="ref", table_name=first_parent_table.name, alias=Fake.word()
    )

    join_query = fql.join_collections(from_table)
    assert isinstance(join_query, QueryExpression)

    second_parent_table = models.Table(name=Fake.word())
    first_parent_table.right_join_table = second_parent_table
    first_parent_table.right_join_key = models.Column(
        name=Fake.word(), table_name=first_parent_table.name, alias=Fake.word()
    )
    second_parent_table.left_join_table = first_parent_table
    second_parent_table.left_join_key = models.Column(
        name="ref", table_name=second_parent_table.name, alias=Fake.word()
    )

    join_query = fql.join_collections(from_table)
    assert isinstance(join_query, QueryExpression)


def test_invalid_join_collections():
    from_table = models.Table(name=Fake.word())
    with pytest.raises(AssertionError):
        fql.join_collections(from_table)

    further_left_table = models.Table(name=Fake.word())
    from_table.left_join_table = further_left_table
    from_table.left_join_key = models.Column(
        name=Fake.word(), table_name=further_left_table.name, alias=Fake.word()
    )
    with pytest.raises(AssertionError):
        fql.join_collections(from_table)


def test_update_documents():
    table_name = Fake.first_name()
    columns = [
        models.Column(
            name=Fake.first_name(), alias=Fake.first_name(), table_name=table_name
        )
        for _ in range(3)
    ]
    table = models.Table(name=table_name, columns=columns)

    update_query = fql.update_documents(table)

    assert isinstance(update_query, QueryExpression)
