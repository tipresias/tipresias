# pylint: disable=missing-docstring,unused-argument

import pytest
from faker import Faker
import numpy as np

from tests.fixtures.factories import MLModelFactory
from tipping.db.faunadb import GraphQLError
from tipping.models import MLModel
from tipping.models.base_model import ValidationError


FAKE = Faker()


@pytest.mark.parametrize(
    ["unique_attribute", "error", "message"],
    [
        ({"name": FAKE.company()}, GraphQLError, r"instance not unique"),
        (
            {"is_principal": True},
            ValidationError,
            r"duplicate principal ML models not allowed",
        ),
        (
            {
                "used_in_competitions": True,
                "prediction_type": np.random.choice(MLModel.PREDICTION_TYPES),
            },
            ValidationError,
            r"duplicate prediction types not allowed for competitions",
        ),
    ],
)
def test_unique_value_constraint(faunadb_client, unique_attribute, error, message):
    MLModelFactory.create(**unique_attribute)
    ml_model = MLModelFactory.build(**unique_attribute)

    # It raises a ValidationError
    with pytest.raises(error, match=message):
        ml_model.create()

    # It doesn't save the ml_model
    query = """
        query {
            allMLModels {
                data {
                    _id
                }
            }
        }
    """
    result = faunadb_client.graphql(query)
    assert len(result["allMLModels"]["data"]) == 1


def test_saving_valid_ml_model(faunadb_client):
    ml_model = MLModelFactory.build()
    saved_ml_model = ml_model.create()

    # It returns the saved ml_model
    assert saved_ml_model == ml_model

    # It saves the ml_model in the DB
    query = "query { findMLModelByID(id: %s) { _id } }" % (saved_ml_model.id)
    result = faunadb_client.graphql(query)
    assert result["findMLModelByID"]["_id"]


def test_fetching_all_ml_models(faunadb_client):
    ml_model_count = np.random.randint(1, 11)

    for _ in range(ml_model_count):
        MLModelFactory.create()

    result = MLModel.all()

    # It returns MLModel objects
    for ml_model in result:
        assert isinstance(ml_model, MLModel)

    # It returns all ML models in the DB
    assert len(result) == ml_model_count


def test_finding_an_ml_model_by_name(faunadb_client):
    ml_models = MLModelFactory.create_batch(3)
    ml_model = ml_models[-1]

    found_ml_model = MLModel.find_by_name(name=ml_model.name)

    # It returns an MLModel instance
    assert isinstance(found_ml_model, MLModel)

    # It returns the queried MLModel record
    assert found_ml_model.name == ml_model.name
