"""Data model for AFL matches."""

from __future__ import annotations

import typing
from datetime import datetime, timedelta, timezone

from sqlalchemy import (
    Column,
    Integer,
    DateTime,
    String,
    ForeignKey,
)
from sqlalchemy.sql import Select, select, func
from sqlalchemy.orm import relationship, validates, session as orm_session

import pandas as pd
from mypy_extensions import TypedDict

from .base import Base, ValidationError
from .team import Team
from .team_match import TeamMatch


MIN_ROUND_NUMBER = 1
MIN_MARGIN = 0
FIRST_ROUND = 1
JAN = 1
FIRST = 1
# Rough estimate, but exactitude isn't necessary here. The AFL fixture tends to separate
# match start times by just under 3 hrs (2:50 - 2:55 from my small sample).
GAME_LENGTH_HRS = 3

FixtureData = TypedDict(
    "FixtureData",
    {
        "date": datetime,
        "year": int,
        "round_number": int,
        "home_team": str,
        "away_team": str,
        "venue": str,
    },
)


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

    _db_session = None

    @classmethod
    def from_future_fixtures(
        cls,
        session: orm_session.Session,
        fixture_matches: pd.DataFrame,
        upcoming_round: int,
    ) -> typing.List[Match]:
        """Create match objects from upcoming fixture data.

        Params:
        -------
        fixture_matches: Data frame of raw fixture data, without match scores.
        upcoming_round: The current round or next if between rounds.

        Returns:
        --------
        None
        """
        right_now = datetime.now(tz=timezone.utc)

        saved_match_count = session.execute(
            select(func.count(Match.id)).where(
                Match.start_date_time > right_now,
                Match.round_number == upcoming_round,
            )
        ).scalar()
        future_matches = fixture_matches.query("date > @right_now")

        if saved_match_count > 0 and saved_match_count == len(future_matches):
            return []

        year = future_matches["year"].max()

        past_matches_this_season = (
            (
                session.execute(
                    select(Match).where(
                        Match.start_date_time < right_now,
                        Match.start_date_time
                        > datetime(right_now.year, JAN, FIRST, tzinfo=timezone.utc),
                    )
                )
            )
            .scalars()
            .all()
        )

        prev_match_this_season = (
            max(past_matches_this_season, key=lambda match: match.start_date_time)
            if any(past_matches_this_season)
            else None
        )

        if prev_match_this_season is not None:
            assert upcoming_round == prev_match_this_season.round_number + 1, (
                "Expected upcoming round number to be 1 greater than previous round "
                f"or 1, but upcoming round is {upcoming_round} in {year}, "
                f" and previous round was {prev_match_this_season.round_number} "
                f"in {prev_match_this_season.start_date_time.year}"
            )

        matches = []

        for fixture_datum in future_matches.to_dict("records"):
            match = Match.get_or_new(
                session,
                start_date_time=fixture_datum["date"],
                round_number=fixture_datum["round_number"],
                venue=fixture_datum["venue"],
            )

            team_matches = TeamMatch.from_fixture(session, fixture_datum)

            for team_match in team_matches:
                match.team_matches.append(team_match)

            matches.append(match)

        return matches

    @classmethod
    def get_or_new(
        cls,
        session: orm_session.Session,
        start_date_time=None,
        round_number=None,
        venue=None,
    ) -> Match:
        """Get or instantiate a match object.

        Params:
        -------
        start_date_time: When the match starts.
        round_number: Round in which the match takes place.
        venue: Stadium where the match is played.

        Returns:
        --------
        A match record.
        """
        raw_date: datetime = (
            start_date_time.to_pydatetime()
            if isinstance(start_date_time, pd.Timestamp)
            else start_date_time
        )

        match_date = raw_date.astimezone(timezone.utc)

        maybe_match = session.execute(
            select(Match).where(
                Match.start_date_time == match_date,
                Match.round_number == int(round_number),
                Match.venue == venue,
            )
        ).scalar()

        if maybe_match:
            return maybe_match

        return Match(
            start_date_time=match_date,
            round_number=int(round_number),
            venue=venue,
        )

    @classmethod
    def played_without_results(cls) -> Select:
        """
        Get all matches that don't have any associated results data.
        Returns:
        --------
        A query set of past matches that haven't been updated with final scores yet.
        """
        right_now = datetime.now(tz=timezone.utc)
        match_duration_ago = right_now - timedelta(hours=GAME_LENGTH_HRS)

        return (
            select(Match)
            .where(Match.start_date_time < match_duration_ago)
            .join(Match.team_matches)
            .where(TeamMatch.score == None)  # pylint: disable=singleton-comparison
            # Filtering by teammatch attributes returns duplicate matches
            # (one for each associated teammatch)
            .distinct()
        )

    @classmethod
    def earliest_without_results(cls) -> Select:
        """
        Get the earliest start_date_time of played matches without results.
        Returns:
        --------
        Date-time for the first past match without scores.
        """
        return cls.played_without_results().order_by(Match.start_date_time).limit(1)

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
