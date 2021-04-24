# pylint: disable=missing-docstring,redefined-outer-name

from unittest.mock import patch

import numpy as np
from faker import Faker
import pytest

from tipping.models.ml_model import MLModel, PredictionType, ValidationError


FAKE = Faker()


def test_ml_model_creation(fauna_session):
    ml_model = MLModel(
        name=FAKE.job(),
        description=FAKE.paragraph(),
        is_principal=False,
        used_in_competitions=False,
        prediction_type=np.random.choice(PredictionType.values()),
    )

    fauna_session.add(ml_model)
    fauna_session.commit()

    assert ml_model.id is not None


@patch("tipping.models.ml_model.Session")
def test_one_principal_validation(MockSession, fauna_session):
    MockSession.return_value = fauna_session

    is_principal = True

    fauna_session.add(
        MLModel(
            name=FAKE.job(),
            description=FAKE.paragraph(),
            is_principal=is_principal,
            used_in_competitions=True,
            prediction_type=np.random.choice(PredictionType.values()),
        )
    )

    with pytest.raises(ValidationError, match=r"Only one principal model is permitted"):
        fauna_session.add(
            MLModel(
                name=FAKE.job(),
                description=FAKE.paragraph(),
                is_principal=is_principal,
                used_in_competitions=True,
                prediction_type=np.random.choice(PredictionType.values()),
            )
        )

        fauna_session.commit()


@patch("tipping.models.ml_model.Session")
def test_unique_competition_prediction_type_validation(MockSession, fauna_session):
    MockSession.return_value = fauna_session

    prediction_type = np.random.choice(PredictionType.values())

    fauna_session.add(
        MLModel(
            name=FAKE.job(),
            description=FAKE.paragraph(),
            is_principal=False,
            used_in_competitions=True,
            prediction_type=prediction_type,
        )
    )

    with pytest.raises(
        ValidationError,
        match=r"Only one of each prediction type is permitted for competitions",
    ):
        fauna_session.add(
            MLModel(
                name=FAKE.job(),
                description=FAKE.paragraph(),
                is_principal=False,
                used_in_competitions=True,
                prediction_type=prediction_type,
            )
        )
        fauna_session.commit()


@patch("tipping.models.ml_model.Session")
def test_principal_used_in_competitions_validation(MockSession, fauna_session):
    MockSession.return_value = fauna_session

    with pytest.raises(
        ValidationError, match=r"A principal model must be used for competitions"
    ):
        fauna_session.add(
            MLModel(
                name=FAKE.job(),
                description=FAKE.paragraph(),
                is_principal=True,
                used_in_competitions=False,
                prediction_type=np.random.choice(PredictionType.values()),
            )
        )

        fauna_session.commit()
