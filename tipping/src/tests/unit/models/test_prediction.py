# pylint: disable=missing-docstring,redefined-outer-name

from unittest import mock

import pytest
from faker import Faker
import numpy as np

from tipping.models.prediction import Prediction
from tipping.models.team import Team, TeamName
from tipping.models.base import ValidationError
from tipping.models import MLModel

Fake = Faker()


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


matching_team_name = TeamName.MELBOURNE.value


@pytest.mark.parametrize(
    ["has_been_played", "is_draw", "winner", "expected_correctness"],
    [
        (False, Fake.pybool(), Team(name=TeamName.HAWTHORN.value), None),
        (True, True, Team(name=TeamName.HAWTHORN.value), True),
        (True, False, Team(name=matching_team_name), True),
        (True, False, Team(name=TeamName.HAWTHORN.value), False),
    ],
)
@mock.patch("tipping.models.match.Match")
def test_update_correctness(
    MockMatch, has_been_played, is_draw, winner, expected_correctness
):
    MockMatch.has_been_played = has_been_played
    MockMatch.is_draw = is_draw
    MockMatch.winner = winner

    prediction = Prediction(
        match=MockMatch,
        ml_model=MLModel(name=Fake.company(), prediction_type="margin"),
        predicted_winner=Team(name=matching_team_name),
    )

    prediction.update_correctness()

    assert prediction.is_correct == expected_correctness
