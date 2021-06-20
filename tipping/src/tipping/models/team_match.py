"""Data model for the join table for matches and teams."""

from __future__ import annotations

import typing

from sqlalchemy import Column, Integer, ForeignKey, Boolean, select
from sqlalchemy.orm import relationship, validates, session as orm_session
import pandas as pd

from .base import Base, ValidationError
from .team import Team


MIN_SCORE = 0


class TeamMatch(Base):
    """Data model for the join table for matches and teams."""

    __tablename__ = "team_matches"

    id = Column(Integer, primary_key=True)
    team_id = Column(Integer, ForeignKey("teams.id"), nullable=False)
    team = relationship(Team)
    match_id = Column(Integer, ForeignKey("matches.id"), nullable=False)
    match = relationship("Match", back_populates="team_matches")
    at_home = Column(Boolean, nullable=False)
    score = Column(Integer, default=0)

    @classmethod
    def from_fixture(
        cls, session: orm_session.Session, fixture_data: pd.Series
    ) -> typing.Tuple[TeamMatch, TeamMatch]:
        """Instantiate home and away team_matches from raw fixture data.

        Params:
        _______
        session: SQLA ORM session
        fixture_data: Raw data for a match

        Returns:
        --------
        tuple of instantiated TeamMatch objects
        """
        return (
            cls._single_team_match_from_fixture(session, fixture_data, at_home=True),
            cls._single_team_match_from_fixture(session, fixture_data, at_home=False),
        )

    @classmethod
    def _single_team_match_from_fixture(
        cls, session: orm_session.Session, fixture_data: pd.Series, at_home: bool
    ) -> TeamMatch:
        team_prefix = "home" if at_home else "away"
        team_name = fixture_data[f"{team_prefix}_team"]
        team = (
            session.execute(select(Team).where(Team.name == team_name)).scalars().one()
        )

        team_score = fixture_data.get(f"{team_prefix}_score", 0)

        return TeamMatch(team=team, at_home=at_home, score=team_score)

    @validates("score")
    def validate_postive_score(self, _key, score):
        """Validate that the score isn't negative."""
        if score >= MIN_SCORE:
            return score

        raise ValidationError(
            f"score {score} is not greater than or equal to {MIN_SCORE}"
        )
