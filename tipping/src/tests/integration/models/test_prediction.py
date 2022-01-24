# pylint: disable=missing-docstring,redefined-outer-name

import numpy as np
from sqlalchemy import sql
from faker import Faker

from tests.fixtures import model_factories, data_factories
from tipping.models.prediction import Prediction


Fake = Faker()


def test_prediction_creation(fauna_session):
    match = model_factories.MatchFactory()
    ml_model = model_factories.MLModelFactory()

    prediction = Prediction(
        match=match,
        ml_model=ml_model,
        predicted_margin=np.random.randint(0, 100),
        predicted_win_probability=np.random.random(),
    )
    fauna_session.add(prediction)
    fauna_session.commit()

    assert prediction.id is not None
    assert prediction.match.id == match.id
    assert prediction.ml_model.id == ml_model.id


def test_get_or_build(fauna_session):
    # Need to turn off autoflush to keep SQLA from saving records before we're ready
    fauna_session.autoflush = False
    ml_model = model_factories.MLModelFactory()
    match = model_factories.FullMatchFactory()
    fauna_session.commit()

    built_prediction = Prediction.get_or_build(
        fauna_session,
        ml_model=ml_model,
        match=match,
    )

    assert ml_model == built_prediction.ml_model
    assert match == built_prediction.match

    prediction_count = fauna_session.execute(
        sql.select(sql.func.count(Prediction.id))
    ).scalar()
    assert prediction_count == 0

    fauna_session.add(built_prediction)
    fauna_session.commit()

    gotten_prediction = Prediction.get_or_build(
        fauna_session,
        ml_model=built_prediction.ml_model,
        match=built_prediction.match,
    )

    assert gotten_prediction == built_prediction


def test_get_by(fauna_session):
    ml_model = model_factories.MLModelFactory()
    predictions = model_factories.PredictionFactory.create_batch(5, ml_model=ml_model)
    prediction = predictions[np.random.randint(1, len(predictions) - 1)]

    blank_prediction = Prediction.get_by(
        fauna_session,
        ml_model=model_factories.MLModelFactory(),
    )

    assert blank_prediction is None

    gotten_prediction = Prediction.get_by(
        fauna_session,
        ml_model=prediction.ml_model,
        match=prediction.match,
        predicted_winner=prediction.predicted_winner,
    )

    assert gotten_prediction == prediction

    gotten_prediction = Prediction.get_by(fauna_session, ml_model=prediction.ml_model)

    assert gotten_prediction == predictions[0]


def test_update_or_create_from_raw_data(fauna_session):
    fixture_data = data_factories.fake_fixture_data()
    prediction_data = data_factories.fake_prediction_data(
        fixtures=fixture_data, pivot_home_away=True
    )

    row_count = fixture_data.shape[0]
    match_idx = Fake.pyint(min_value=0, max_value=row_count - 1)
    match_prediction_data = prediction_data.iloc[match_idx, :]

    for idx, match_datum in fixture_data.iloc[
        match_idx - 5 : min(match_idx + 5, row_count - 1), :
    ].iterrows():
        match = model_factories.FullMatchFactory(
            start_date_time=match_datum["date"],
            round_number=match_datum["round_number"],
            venue=match_datum["venue"],
            home_team_match__team=model_factories.TeamFactory(
                name=match_datum["home_team"]
            ),
            away_team_match__team=model_factories.TeamFactory(
                name=match_datum["away_team"]
            ),
        )
        if idx == match_idx:
            predicted_match = match

    ml_model = model_factories.MLModelFactory(name=match_prediction_data["ml_model"])
    fauna_session.commit()

    created_prediction = Prediction.update_or_create_from_raw_data(
        fauna_session, match_prediction_data
    )

    assert created_prediction.match == predicted_match
    assert created_prediction.ml_model == ml_model

    updated_prediction = Prediction.update_or_create_from_raw_data(
        fauna_session, match_prediction_data
    )
    assert updated_prediction == created_prediction
