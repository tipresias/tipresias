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
def test_parsing_unsupported_where(filter_params):
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
def test_parsing_where(filter_params, column_params):
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
