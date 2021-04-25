# pylint: disable=missing-docstring,redefined-outer-name

from datetime import timezone

import numpy as np
from faker import Faker
import pytest

from tipping.models.prediction import Prediction
from tipping.models.ml_model import MLModel, PredictionType
from tipping.models.match import Match


FAKE = Faker()


@pytest.fixture
def match():
    return Match(
        start_date_time=FAKE.date_time(tzinfo=timezone.utc),
        round_number=np.random.randint(1, 100),
        venue=FAKE.company(),
    )


@pytest.fixture
def ml_model():
    return MLModel(
        name=FAKE.job(),
        description=FAKE.paragraph(),
        is_principal=False,
        used_in_competitions=False,
        prediction_type=np.random.choice(PredictionType.values()),
    )


def test_prediction_creation(fauna_session, match, ml_model):
    fauna_session.add(match)
    fauna_session.add(ml_model)
    fauna_session.commit()

    prediction = Prediction(
        match_id=match.id,
        ml_model_id=ml_model.id,
        predicted_margin=np.random.randint(0, 100),
        predicted_win_probability=np.random.random(),
    )
    fauna_session.add(prediction)
    fauna_session.commit()

    assert prediction.id is not None
    assert prediction.match.id == match.id
    assert prediction.ml_model.id == ml_model.id
