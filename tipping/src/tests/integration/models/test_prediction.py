# pylint: disable=missing-docstring

from faker import Faker
import numpy as np

from tests.fixtures.factories import PredictionFactory, MatchFactory, MLModelFactory


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
