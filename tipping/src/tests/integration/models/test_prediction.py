# pylint: disable=missing-docstring,redefined-outer-name

import numpy as np
from sqlalchemy import sql
from faker import Faker

from tests.fixtures import model_factories
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
