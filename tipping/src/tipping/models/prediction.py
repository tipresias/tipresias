"""Data model for the join table for matches and teams."""

from sqlalchemy import Column, Integer, ForeignKey, Boolean, Float
from sqlalchemy.orm import relationship, validates

from tipping.models.base import Base, ValidationError
from tipping.models.ml_model import MLModel
from tipping.models.match import Match
from tipping.models.team import Team


MIN_PREDICTED_MARGIN = 0
MIN_PROBABILITY = 0
MAX_PROBABILITY = 1


class Prediction(Base):
    """Model for ML model predictions for each match."""

    __tablename__ = "predictions"

    id = Column(Integer, primary_key=True)
    match_id = Column(Integer, ForeignKey("matches.id"), nullable=False)
    match = relationship(Match, back_populates="predictions")
    ml_model_id = Column(Integer, ForeignKey("ml_models.id"), nullable=False)
    ml_model = relationship(MLModel, back_populates="predictions")
    predicted_winner_id = Column(Integer, ForeignKey("teams.id"))
    predicted_winner = relationship(Team)

    predicted_margin = Column(Integer)
    predicted_win_probability = Column(Float)
    is_correct = Column(Boolean)

    @validates("predicted_margin")
    def validate_predicted_margin(self, _key, value):
        """Validate that the predicted margin isn't negative."""
        if value is None or value >= MIN_PREDICTED_MARGIN:
            return value

        raise ValidationError(
            f"predicted_margin '{value}' must be greater than or equal to 0."
        )

    @validates("predicted_win_probability")
    def validate_predicted_win_probability(self, _key, value):
        """Validate that the predicted win probability is within the valid range."""
        if MIN_PROBABILITY <= value <= MAX_PROBABILITY:
            return value

        raise ValidationError(
            f"predicted_win_probability '{value}' must be between 0 and 1 "
            "(inclusive)."
        )
