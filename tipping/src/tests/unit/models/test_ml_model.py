# pylint: disable=missing-docstring,redefined-outer-name
from unittest.mock import patch, MagicMock

import pytest
from faker import Faker
import numpy as np

from tipping.models.ml_model import MLModel, ValidationError, PredictionType

FAKE = Faker()

DEFAULT_INPUT = {
    "name": FAKE.job(),
    "description": FAKE.paragraph(),
    "is_principal": False,
    "used_in_competitions": False,
    "prediction_type": np.random.choice(PredictionType.values()),
}


@patch("tipping.models.ml_model.MLModel._fetch_one", MagicMock())
def test_prediction_type_validation():
    with pytest.raises(ValidationError, match=r"prediction_type color is not"):
        MLModel(
            **{
                **DEFAULT_INPUT,
                "prediction_type": "color",
            }
        )
