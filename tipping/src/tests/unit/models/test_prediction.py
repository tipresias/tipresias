# pylint: disable=missing-docstring,redefined-outer-name

import pytest
from faker import Faker
import numpy as np

from tipping.models.prediction import Prediction, ValidationError


FAKE = Faker()


@pytest.mark.parametrize(
    "attribute,error_message",
    [
        (
            {"predicted_margin": np.random.randint(-100, 0)},
            r"must be greater than or equal to 0",
        ),
        (
            {
                "predicted_win_probability": np.random.random()
                + np.random.randint(2, 100)
            },
            r"must be between 0 and 1",
        ),
        (
            {
                "predicted_win_probability": np.random.random()
                - np.random.randint(2, 100)
            },
            r"must be between 0 and 1",
        ),
    ],
)
def test_prediction_validation(attribute, error_message):
    default_input = {
        "match_id": np.random.randint(1, 100),
        "ml_model_id": np.random.randint(1, 100),
        "predicted_margin": np.random.randint(0, 100),
        "predicted_win_probability": np.random.random(),
    }

    with pytest.raises(ValidationError, match=error_message):
        Prediction(
            **{
                **default_input,
                **attribute,
            }
        )
