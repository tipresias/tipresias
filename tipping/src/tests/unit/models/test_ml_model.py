# pylint: disable=missing-docstring

from unittest.mock import patch

import pytest
from faker import Faker

from tests.fixtures.factories import MLModelFactory
from tipping.models.base_model import ValidationError
from tipping.models import MLModel


FAKE = Faker()


@pytest.mark.parametrize(
    ["invalid_attribute", "error_message"],
    [
        ({"name": ""}, "empty values not allowed"),
        ({"name": None}, "null value not allowed"),
        ({"name": 42}, "string"),
        ({"prediction_type": "good"}, "unallowed value good"),
    ],
)
@patch("tipping.models.base_model.FaunadbClient.graphql")
def test_saving_invalid_ml_model(mock_graphql, invalid_attribute, error_message):
    ml_model = MLModelFactory.build(**invalid_attribute)

    # It raises a ValidateionError
    with pytest.raises(ValidationError, match=error_message):
        ml_model.create()

    # It doesn't save the ml_model
    mock_graphql.assert_not_called()


def test_from_db_response():
    ml_model = MLModelFactory.build(add_id=True)
    db_record = {
        "name": ml_model.name,
        "isPrincipal": ml_model.is_principal,
        "usedInCompetitions": ml_model.used_in_competitions,
        "predictionType": ml_model.prediction_type,
        "_id": ml_model.id,
    }

    ml_model_from_record = MLModel.from_db_response(db_record)

    # It returns an ml_model object
    assert isinstance(ml_model_from_record, MLModel)

    # It has matching attributes
    assert ml_model.attributes == ml_model_from_record.attributes
