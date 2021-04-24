# SQLAlchemy query syntax depends on class.attribute == value,
# so we can't use "is True"
# pylint: disable=singleton-comparison
"""Data model for machine-learning models/estimators."""

from typing import List
import enum

from sqlalchemy import inspect, select, Column, String, Text, Integer, Boolean
from sqlalchemy.orm import validates

from tipping.models.base import Base, ValidationError
from tipping.settings import Session


class PredictionType(enum.Enum):
    """
    Enum for different prediction types.

    Correspond to 'predicted_<prediction type>' fields on the Prediction model.
    """

    MARGIN = "margin"
    WIN_PROBABILITY = "win_probability"

    @classmethod
    def has_value(cls, name: str) -> bool:
        """Determines whether the given name is a TeamName value."""
        return name in cls.values()

    @classmethod
    def values(cls) -> List:
        """Returns all name values in TeamName."""
        return [member.value for member in cls]


class MLModel(Base):
    """
    Data model for machine-learning models/estimators.

    Attributes:
    -----------
    name: Name of the model.
    description: Optional description to provide more information about the model.
    is_principal: Whether the model's predicted winners represent the official
        predicted winners of Tipresias.
    used_in_competitions: Whether the model's predictions are submitted for competitions.
    """

    __tablename__ = "ml_models"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False, unique=True)
    description = Column(Text)
    is_principal = Column(Boolean, nullable=False, default=False, index=True)
    used_in_competitions = Column(Boolean, nullable=False, default=False, index=True)
    prediction_type = Column(String, nullable=False, index=True)

    _session = None

    @validates("is_principal", "used_in_competitions", "prediction_type")
    def validate_competition_attributes(self, key, value):
        """Validates that a principal model is used in competitions."""
        is_principal = value if key == "is_principal" else self.is_principal
        self._validate_one_principal(is_principal)

        prediction_type = value if key == "prediction_type" else self.prediction_type
        self._validate_prediction_type(prediction_type)

        used_in_competitions = (
            value if key == "used_in_competitions" else self.used_in_competitions
        )
        self._validate_unique_competition_prediction_type(
            used_in_competitions, prediction_type
        )

        if is_principal is True and used_in_competitions is False:
            raise ValidationError("A principal model must be used for competitions.")

        return value

    def _validate_one_principal(self, is_principal):
        """Validates that there's only one principal model in the DB."""
        if not is_principal:
            return None

        principal_model = self._fetch_one(
            select(self.__class__).where(self.__class__.is_principal == True)
        )

        if not principal_model or principal_model.id == self.id:
            return None

        raise ValidationError(
            f"Only one principal model is permitted, but "
            f"{principal_model.name} is already a principal model."
        )

    def _validate_unique_competition_prediction_type(
        self, used_in_competitions, prediction_type
    ):
        if not used_in_competitions or prediction_type is None:
            return None

        statement = select(self.__class__).where(
            self.__class__.used_in_competitions == True,
            self.__class__.prediction_type == prediction_type,
        )

        # breakpoint()

        matching_competition_prediction_type = self._fetch_one(statement)

        if (
            not matching_competition_prediction_type
            or matching_competition_prediction_type.id == self.id
        ):
            return None

        raise ValidationError(
            "Only one of each prediction type is permitted for competitions, "
            f"but {matching_competition_prediction_type.name} is already "
            f"predicting {matching_competition_prediction_type.prediction_type} "
            "for competitions."
        )

    @staticmethod
    def _validate_prediction_type(prediction_type):
        if prediction_type is None or PredictionType.has_value(prediction_type):
            return None

        raise ValidationError(
            f"prediction_type {prediction_type} is not in the list "
            f"of valid values {PredictionType.values()}."
        )

    def _fetch_one(self, sql_statement: str) -> "MLModel":
        self._session = self._session or inspect(self).session or Session()
        return self._session.execute(sql_statement).scalars().first()
