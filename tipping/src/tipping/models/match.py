"""Data model for AFL matches."""

from __future__ import annotations

import typing
from datetime import datetime, timedelta, timezone
from warnings import warn
import functools

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
WEEK_IN_DAYS = 7
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
            raw_date: typing.Optional[datetime] = (
                fixture_datum["date"].to_pydatetime()
                if isinstance(fixture_datum["date"], pd.Timestamp)
                else fixture_datum["date"]
            )
            match_date = (
                raw_date if raw_date is None else raw_date.astimezone(timezone.utc)
            )
            round_number = int(fixture_datum["round_number"])
            match = Match.get_or_build(
                session,
                start_date_time=match_date,
                round_number=round_number,
                venue=fixture_datum["venue"],
            )

            team_matches = TeamMatch.from_fixture(session, fixture_datum)

            for team_match in team_matches:
                match.team_matches.append(team_match)

            matches.append(match)

        return matches

    @classmethod
    def get_by(
        cls,
        session: orm_session.Session,
        start_date_time: typing.Optional[datetime] = None,
        round_number: typing.Optional[int] = None,
        venue: typing.Optional[str] = None,
    ) -> typing.Optional[Match]:
        """Get a match object from the DB that matches the given attributes.

        Params:
        -------
        start_date_time: When the match starts.
        round_number: Round in which the match takes place.
        venue: Stadium where the match is played.

        Returns:
        --------
        Match instance or None if no record matches the params.
        """
        conditions = []
        if start_date_time is not None:
            conditions.append(cls.start_date_time == start_date_time)
        if round_number is not None:
            conditions.append(cls.round_number == round_number)
        if venue is not None:
            conditions.append(cls.venue == venue)

        return session.execute(select(cls).where(*conditions)).scalar()

    @classmethod
    def get_or_build(
        cls,
        session: orm_session.Session,
        start_date_time: typing.Optional[datetime] = None,
        round_number: typing.Optional[int] = None,
        venue: typing.Optional[str] = None,
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
        maybe_match = cls.get_by(
            session,
            start_date_time=start_date_time,
            round_number=round_number,
            venue=venue,
        )

        if maybe_match:
            return maybe_match

        return Match(
            start_date_time=start_date_time,
            round_number=round_number,
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

    @classmethod
    def update_results(cls, matches: typing.List[Match], match_results: pd.DataFrame):
        """
        Fill in match results data for all matches that have been played.

        Params:
        -------
        matches: List of match objects without saved results.
        match_results: Raw match results data.
        """
        for match in matches:
            match_result = match_results.query(
                "year == @match.year & "
                "round_number == @match.round_number & "
                "home_team == @match.team(at_home=True).name & "
                "away_team == @match.team(at_home=False).name"
            )

            match.update_result(match_result)

    def update_result(self, match_result: pd.DataFrame):
        """
        Fill in match results data for a match that's been played.

        Params:
        -------
        match_result: Raw data for a single match.
        """
        if not self.has_been_played or not self._validate_results_data_presence(
            match_result
        ):
            return None

        self._validate_one_result_row(match_result)

        for team_match in self.team_matches:
            team_match.update_score(match_result.iloc[0, :])

        self._save_result()

        for prediction in self.predictions:
            prediction.update_correctness()

        return None

    @property
    def has_been_played(self) -> bool:
        """Whether a match has been played yet."""
        match_end_time = self.start_date_time + timedelta(hours=GAME_LENGTH_HRS)
        return match_end_time < datetime.now(tz=timezone.utc)

    @property
    def is_draw(self) -> bool:
        """Indicate whether a match result was a draw."""
        return self.has_results and functools.reduce(
            lambda score_x, score_y: score_x == score_y, self._match_scores
        )

    @property
    def has_results(self) -> bool:
        """Whether a match has a final score."""
        return self.has_been_played and self._has_score

    @property
    def year(self) -> int:
        """The year in which the match is played."""
        return self.start_date_time.year

    def team(self, at_home: typing.Optional[bool] = None) -> Team:
        """The home or away team for this match."""
        if at_home is None:
            raise ValueError("Must pass a boolean value for at_home")

        return next(
            team_match.team
            for team_match in self.team_matches
            if team_match.at_home == at_home
        )

    @property
    def _has_score(self) -> bool:
        return any(score is not None for score in self._match_scores)

    @property
    def _match_scores(self):
        return [team_match.score for team_match in self.team_matches]

    def _save_result(self):
        self.margin = self._calculate_margin()
        self.winner = self._calculate_winner()

    def _calculate_margin(self):
        if not any(self._match_scores):
            return None

        return functools.reduce(
            lambda score_x, score_y: abs(score_x - score_y), self._match_scores
        )

    def _calculate_winner(self):
        """Return the record for the winning team of the match."""
        if not any(self._match_scores) or self.is_draw:
            return None

        return max(self.team_matches, key=lambda tm: tm.score).team

    def _validate_results_data_presence(self, match_result: pd.DataFrame) -> bool:
        # AFLTables usually updates match results a few days after the round
        # is finished. Allowing for the occasional delay, we accept matches without
        # results data for a week before raising an error.
        if (
            self.start_date_time
            > datetime.now(tz=timezone.utc) - timedelta(days=WEEK_IN_DAYS)
            and not match_result.size
        ):
            warn(
                f"Unable to update the match between {self.team(at_home=True).name} "
                f"and {self.team(at_home=False).name} from round {self.round_number}. "
                "This is likely due to AFLTables not having updated the match results "
                "yet."
            )

            return False

        team_match_info = [
            {"team": team_match.team.name, "at_home": team_match.at_home}
            for team_match in self.team_matches
        ]
        assert match_result.size, (
            "Didn't find any match data rows that matched match record:\n"
            "{\n"
            f"\tstart_date_time: {self.start_date_time},\n"
            f"\tround_number: {self.round_number},\n"
            f"\tvenue: {self.venue},\n"
            f"\tteam_matches: {team_match_info}"
            "}"
        )

        return True

    @staticmethod
    def _validate_one_result_row(match_result: pd.DataFrame):
        assert len(match_result) == 1, (
            "Filtering match results by year, round_number and team name "
            "should result in a single row, but instead the following was "
            "returned:\n"
            f"{match_result}"
        )

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
        if margin is None or margin >= MIN_MARGIN:
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
