# pylint: disable=missing-docstring,redefined-outer-name

import numpy as np

from tests.fixtures import model_factories
from tipping.models.prediction import Prediction


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
