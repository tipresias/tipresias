# pylint: disable=missing-docstring

from faker import Faker
import numpy as np
import pandas as pd

from tests.fixtures.factories import PredictionFactory, MatchFactory, MLModelFactory
from tests.fixtures.data_factories import fake_prediction_data
from tipping.models import Prediction

FAKE = Faker()


def test_saving_valid_prediction(faunadb_client):
    match = MatchFactory.create()
    ml_model = MLModelFactory.create()
    predicted_winner = np.random.choice(match.team_matches).team
    prediction = PredictionFactory.build(
        match=match, ml_model=ml_model, predicted_winner=predicted_winner
    )
    saved_prediction = prediction.create()

    # It returns the saved prediction
    assert saved_prediction == prediction

    # It saves the prediction in the DB
    query = "query { findPredictionByID(id: %s) { _id } }" % (saved_prediction.id)
    result = faunadb_client.graphql(query)
    assert result["findPredictionByID"]["_id"]


def test_updating_valid_prediction(faunadb_client):  # pylint: disable=unused-argument
    original_predicted_margin = np.random.random() * 50
    prediction = PredictionFactory.create(
        predicted_margin=original_predicted_margin, was_correct=None
    )
    updated_was_correct = True
    prediction.was_correct = updated_was_correct
    updated_predicted_margin = original_predicted_margin + 5
    updated_prediction = prediction.update(predicted_margin=updated_predicted_margin)

    # It returns a prediction
    assert isinstance(updated_prediction, Prediction)

    # The returned prediction has the updated attribute values
    assert updated_prediction.was_correct == updated_was_correct
    assert updated_prediction.predicted_margin == updated_predicted_margin

    # The original prediction has updated attribute values
    assert prediction.was_correct == updated_was_correct
    assert prediction.predicted_margin == updated_predicted_margin


def test_updating_or_creating_prediction_from_raw_data(faunadb_client):
    ml_model = MLModelFactory.create()
    match = MatchFactory.create()
    prediction_data = fake_prediction_data(
        ml_model_name=ml_model.name, pivot_home_away=True
    )

    old_prediction_data = prediction_data.iloc[0, :].to_dict()
    old_prediction_data["year"] = match.season
    old_prediction_data["round_number"] = match.round_number
    for team_match in match.team_matches:
        if team_match.at_home:
            old_prediction_data["home_team"] = team_match.team.name
        else:
            old_prediction_data["away_team"] = team_match.team.name

    created_prediction = Prediction.update_or_create_from_raw_data(
        pd.Series(old_prediction_data)
    )

    # It saves the prediction in the DB
    query = "query { findPredictionByID(id: %s) { _id } }" % (created_prediction.id)
    result = faunadb_client.graphql(query)
    assert result["findPredictionByID"]["_id"]

    new_prediction_data = prediction_data.iloc[1, :]

    updated_prediction = Prediction.update_or_create_from_raw_data(
        pd.Series(
            {
                **old_prediction_data,
                **{
                    "home_predicted_margin": new_prediction_data[
                        "home_predicted_margin"
                    ],
                    "home_predicted_win_probability": new_prediction_data[
                        "home_predicted_win_probability"
                    ],
                },
            }
        )
    )

    # It updates the same prediction
    assert created_prediction.id == updated_prediction.id
    assert (
        updated_prediction.predicted_margin is None
        or created_prediction.predicted_margin != updated_prediction.predicted_margin
    )
    assert (
        updated_prediction.predicted_win_probability is None
        or created_prediction.predicted_win_probability
        != updated_prediction.predicted_win_probability
    )
