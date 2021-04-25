"""Data model for AFL matches."""

from datetime import datetime, timedelta

from sqlalchemy import Column, Integer, DateTime, String, ForeignKey
from sqlalchemy.orm import relationship, validates

from tipping.models.base import Base, ValidationError
from tipping.models.team import Team


MIN_ROUND_NUMBER = 1
MIN_MARGIN = 0


class Match(Base):
    """Data model for AFL matches."""

    __tablename__ = "matches"

    id = Column(Integer, primary_key=True)
    start_date_time = Column(DateTime)
    round_number = Column(Integer)
    venue = Column(String)
    margin = Column(Integer)
    winner_id = Column(Integer, ForeignKey("teams.id"))
    winner = relationship(Team)
    team_matches = relationship("TeamMatch", back_populates="match")
    predictions = relationship("Prediction", back_populates="match")

    @validates("round_number")
    def validate_at_least_min_round(self, _key, round_number):
        """Validate that the round number is >= 1."""
        if round_number >= MIN_ROUND_NUMBER:
            return round_number

        raise ValidationError(
            f"round_number {round_number} is not greater than or equal to "
            f"{MIN_ROUND_NUMBER}"
        )

    @validates("margin")
    def validate_postive_margin(self, _key, margin):
        """Validate that the margin isn't negative."""
        if margin >= MIN_MARGIN:
            return margin

        raise ValidationError(
            f"margin {margin} is not greater than or equal to {MIN_MARGIN}"
        )

    @validates("start_date_time")
    def validate_utc(self, _key, start_date_time):
        """Validate that start_date_time is always UTC for consistency."""
        if datetime.utcoffset(start_date_time) == timedelta(0):
            return start_date_time

        raise ValidationError(
            f"start_date_time {start_date_time} is not set to the UTC"
        )
