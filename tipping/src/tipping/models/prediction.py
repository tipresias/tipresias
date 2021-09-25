"""Data model for the join table for matches and teams."""

from __future__ import annotations

import typing

from mypy_extensions import TypedDict
from sqlalchemy import Column, Integer, ForeignKey, Boolean, Float, orm, sql

from . import base
from .match import Match
from .ml_model import MLModel
from .team import Team

PredictionAttributes = TypedDict(
    "PredictionAttributes",
    {
        "match_id": int,
        "ml_model_id": int,
        "predicted_winner_id": int,
        "predicted_margin": typing.Optional[float],
        "predicted_win_probability": typing.Optional[float],
        "is_correct": typing.Optional[bool],
    },
)

MIN_PREDICTED_MARGIN = 0
MIN_PROBABILITY = 0
MAX_PROBABILITY = 1

JAN = 1
FIRST = 1


class Prediction(base.Base):
    """Model for ML model predictions for each match."""

    __tablename__ = "predictions"

    id = Column(Integer, primary_key=True)
    match_id = Column(Integer, ForeignKey("matches.id"), nullable=False)
    match = orm.relationship(Match, back_populates="predictions")
    ml_model_id = Column(Integer, ForeignKey("ml_models.id"), nullable=False)
    ml_model = orm.relationship(MLModel, back_populates="predictions")
    predicted_winner_id = Column(Integer, ForeignKey("teams.id"))
    predicted_winner = orm.relationship(Team)

    predicted_margin = Column(Integer)
    predicted_win_probability = Column(Float)
    is_correct = Column(Boolean)

    @classmethod
    def get_by(
        cls, session: orm.session.Session, **prediction_attributes: PredictionAttributes
    ) -> typing.Optional[Prediction]:
        """Get a Prediction object from the DB that matches the given attributes.

        Params:
        -------
        match_id: ID of the associated Match.
        ml_model_id: ID of the associated MLMOdel
        predicted_winner_id: ID of the associated Team that is the predicted winner.
        predicted_margin: Predicted margin of victory.
        predicted_win_probability: Predicted win probability.
        is_correct: Whether the prediction is correct.

        Returns:
        --------
        Prediction instance or None if no record matches the params.
        """
        conditions = [
            getattr(cls, key) == value for key, value in prediction_attributes.items()
        ]
        return session.execute(sql.select(cls).where(*conditions)).scalar()

    @classmethod
    def get_or_build(
        cls, session: orm.session.Session, **prediction_attributes: PredictionAttributes
    ) -> Prediction:
        """Get or instantiate a match object.

        Params:
        -------
        match: The associated Match.
        ml_model: The associated MLModel
        predicted_winner: The associated Team that is the predicted winner.
        predicted_margin: Predicted margin of victory.
        predicted_win_probability: Predicted win probability.
        is_correct: Whether the prediction is correct.

        Returns:
        --------
        A Prediction record.
        """
        maybe_prediction = cls.get_by(session, **prediction_attributes)

        if maybe_prediction:
            return maybe_prediction

        return cls(**prediction_attributes)

    def update_correctness(self):
        """Update the is_correct attribute based on associated team_match scores."""
        if not self.match.has_been_played:
            self.is_correct = None
            return None

        # In footy tipping competitions its typical to grant everyone a correct tip
        # in the case of a draw
        self.is_correct = (
            self.match.is_draw or self.predicted_winner.name == self.match.winner.name
        )
        return None

    @orm.validates("predicted_margin")
    def validate_predicted_margin(self, _key, value):
        """Validate that the predicted margin isn't negative."""
        if value is None or value >= MIN_PREDICTED_MARGIN:
            return value

        raise base.ValidationError(
            f"predicted_margin '{value}' must be greater than or equal to 0."
        )

    @orm.validates("predicted_win_probability")
    def validate_predicted_win_probability(self, _key, value):
        """Validate that the predicted win probability is within the valid range."""
        if value is None or MIN_PROBABILITY <= value <= MAX_PROBABILITY:
            return value

        raise base.ValidationError(
            f"predicted_win_probability '{value}' must be between 0 and 1 "
            "(inclusive)."
        )
