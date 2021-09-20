# pylint: disable=missing-docstring,redefined-outer-name

from unittest.mock import patch

import numpy as np
from faker import Faker
import pytest

from tests.fixtures import model_factories
from tipping.models.ml_model import MLModel, PredictionType, ValidationError


Fake = Faker()


def test_ml_model_creation(fauna_session):
    ml_model = MLModel(
        name=Fake.job(),
        description=Fake.paragraph(),
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
            name=Fake.job(),
            description=Fake.paragraph(),
            is_principal=is_principal,
            used_in_competitions=True,
            prediction_type=np.random.choice(PredictionType.values()),
        )
    )

    with pytest.raises(ValidationError, match=r"Only one principal model is permitted"):
        fauna_session.add(
            MLModel(
                name=Fake.job(),
                description=Fake.paragraph(),
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
            name=Fake.job(),
            description=Fake.paragraph(),
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
                name=Fake.job(),
                description=Fake.paragraph(),
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
                name=Fake.job(),
                description=Fake.paragraph(),
                is_principal=True,
                used_in_competitions=False,
                prediction_type=np.random.choice(PredictionType.values()),
            )
        )

        fauna_session.commit()


def test_get_by(fauna_session):
    ml_models = model_factories.MLModelFactory.create_batch(
        5, used_in_competitions=True
    )
    ml_model = ml_models[np.random.randint(1, len(ml_models) - 1)]

    blank_ml_model = MLModel.get_by(
        fauna_session,
        name=Fake.bs(),
    )

    assert blank_ml_model is None

    gotten_ml_model = MLModel.get_by(
        fauna_session, name=ml_model.name, prediction_type=ml_model.prediction_type
    )

    assert gotten_ml_model == ml_model

    gotten_ml_model = MLModel.get_by(fauna_session, used_in_competitions=True)

    assert gotten_ml_model == ml_models[0]
