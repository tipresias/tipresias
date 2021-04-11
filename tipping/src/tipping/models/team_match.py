"""Data model for the join table for matches and teams."""

from sqlalchemy import Column, Integer, ForeignKey, Boolean
from sqlalchemy.orm import relationship, validates

from tipping.models.base import Base, ValidationError
from tipping.models.team import Team
from tipping.models.match import Match


MIN_SCORE = 0


class TeamMatch(Base):
    """Data model for the join table for matches and teams."""

    __tablename__ = "team_matches"

    id = Column(Integer, primary_key=True)
    team_id = Column(Integer, ForeignKey("teams.id"), nullable=False)
    team = relationship(Team)
    match_id = Column(Integer, ForeignKey("matches.id"), nullable=False)
    match = relationship(Match, back_populates="team_matches")
    at_home = Column(Boolean, nullable=False)
    score = Column(Integer, default=0)

    @validates("score")
    def validate_postive_score(self, _key, score):
        """Validate that the score isn't negative."""
        if score >= MIN_SCORE:
            return score

        raise ValidationError(
            f"score {score} is not greater than or equal to {MIN_SCORE}"
        )
