# pylint: disable=missing-docstring,unused-argument

from unittest.mock import patch

import pytest
from faker import Faker

from tests.fixtures.factories import (
    PredictionFactory,
    MatchFactory,
    TeamFactory,
    MLModelFactory,
)
from tests.helpers.model_helpers import assert_deep_equal_attributes
from tipping.models.base_model import ValidationError
from tipping.models import Prediction


FAKE = Faker()


@pytest.mark.parametrize(
    ["invalid_attribute", "error_message"],
    [
        ({"predicted_margin": -5.3}, "min value is 0.0"),
        ({"predicted_win_probability": -0.3}, "min value is 0.0"),
    ],
)
@patch("tipping.models.base_model.FaunadbClient.graphql")
def test_creating_invalid_prediction(mock_graphql, invalid_attribute, error_message):
    prediction = PredictionFactory.build(**invalid_attribute)

    # It raises a ValidateionError
    with pytest.raises(ValidationError, match=error_message):
        prediction.create()

    # It doesn't save the prediction
    mock_graphql.assert_not_called()


@pytest.mark.parametrize(
    ["invalid_attribute", "error_message"],
    [
        (
            {"predicted_margin": -5.3},
            "min value is 0.0",
        ),
        (
            {"predicted_win_probability": -0.3},
            "min value is 0.0",
        ),
        ({"not_a_real": "attribute"}, "unknown field"),
    ],
)
@patch("tipping.models.base_model.FaunadbClient.graphql")
def test_updating_invalid_prediction(mock_graphql, invalid_attribute, error_message):
    prediction = PredictionFactory.build(add_id=True)

    # It raises a ValidationError
    with pytest.raises(ValidationError, match=error_message):
        prediction.update(**invalid_attribute)

    # It doesn't save the prediction
    mock_graphql.assert_not_called()


def test_from_db_response():
    match = MatchFactory.build(add_id=True, team_matches__add_id=True)
    ml_model = MLModelFactory.build(add_id=True)
    predicted_winner = TeamFactory.build(add_id=True)
    prediction = PredictionFactory.build(
        match=match, ml_model=ml_model, predicted_winner=predicted_winner, add_id=True
    )
    db_record = {
        "_id": prediction.id,
        "match": {
            "startDateTime": match.start_date_time.isoformat(),
            "season": match.season,
            "roundNumber": match.round_number,
            "venue": match.venue,
            "margin": match.margin,
            "winner": None
            if match.winner is None
            else {"name": match.winner.name, "_id": match.winner.id},
            "_id": match.id,
            "teamMatches": {
                "data": [
                    {
                        "atHome": tm.at_home,
                        "score": tm.score,
                        "team": {"_id": tm.team.id, "name": tm.team.name},
                        "_id": tm.id,
                    }
                    for tm in match.team_matches
                ]
            },
        },
        "mlModel": {
            "_id": ml_model.id,
            "name": ml_model.name,
            "predictionType": ml_model.prediction_type,
            "isPrincipal": ml_model.is_principal,
            "usedInCompetitions": ml_model.used_in_competitions,
        },
        "predictedWinner": {"_id": predicted_winner.id, "name": predicted_winner.name},
        "predictedMargin": prediction.predicted_margin,
        "predictedWinProbability": prediction.predicted_win_probability,
        "wasCorrect": prediction.was_correct,
    }

    prediction_from_record = Prediction.from_db_response(db_record)

    # It returns an prediction object
    assert isinstance(prediction_from_record, Prediction)

    # It has matching attributes
    assert_deep_equal_attributes(prediction, prediction_from_record)


@patch("tipping.models.base_model.FaunadbClient.graphql")
def test_updating_correctness(mock_graphql):
    prediction = PredictionFactory.build(add_id=True)

    was_correct = prediction.was_correct
    prediction.was_correct = not was_correct

    prediction.update_correctness()

    # It updates correctness per associated match results
    assert prediction.was_correct == was_correct
