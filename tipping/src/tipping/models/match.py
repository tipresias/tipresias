"""Data model for AFL matches."""

from __future__ import annotations
from typing import Optional, Dict, Any, Union, Sequence, List
from datetime import datetime, timedelta, timezone
from dateutil import parser

from cerberus import Validator, TypeDefinition
import numpy as np
import pandas as pd

from tipping.types import FixtureData, MatchData
from .team import Team
from .base_model import BaseModel


class _MatchRecordCollection:
    """Collection of match match objects associated with records in FaunaDB."""

    def __init__(self, records: Sequence[Optional[Match]]):
        """
        Params:
        -------
        records: List of Match objects created from FaunaDB match records.
        """
        self.records = records

    def count(self) -> int:
        """Get the number of model objects in the collection.

        Returns:
        --------
        Count of records.
        """
        return len(self.records)

    def filter(self, **kwargs) -> _MatchRecordCollection:
        """Filter collection objects by attribute values.

        Params:
        -------
        Attribute key/value pairs.

        Returns:
        --------
        The filtered collection.
        """
        filtered_records = [
            record
            for record in self.records
            if self._attributes_match(record, **kwargs)
        ]

        return self.__class__(records=filtered_records)

    @staticmethod
    def _attributes_match(record, **kwargs) -> bool:
        return all([getattr(record, key) == val for key, val in kwargs.items()])

    def __len__(self):
        return len(self.records)

    def __iter__(self):
        return (record for record in self.records)

    def __array__(self):
        return np.array(list(self.records))

    def __getitem__(self, key):
        return self.records[key]


class TeamMatch(BaseModel):
    """Data model for the connection between matches and teams."""

    def __init__(
        self,
        team: Optional[Team] = None,
        match: Optional[Match] = None,
        at_home: Optional[bool] = None,
        score: int = 0,
    ):
        """
        Params:
        -------
        team: The associated Team,
        match: The associated Match,
        at_home: Whether the Team is playing at home for the given Match,
        score: How many points the Team scored during the given Match,
        """
        team_type = TypeDefinition("team", (Team,), ())
        Validator.types_mapping["team"] = team_type

        match_type = TypeDefinition("match", (Match,), ())
        Validator.types_mapping["match"] = match_type

        super().__init__(Validator)

        self.team = team
        self.match = match
        self.at_home = at_home
        self.score = score
        self.id = None

        if self.match is not None:
            self.match.team_matches.append(self)

    @classmethod
    def from_db_response(cls, record: Dict[str, Any]) -> TeamMatch:
        """Convert a DB record object into an instance of TeamMatch.

        Params:
        -------
        record: GraphQL response dictionary that represents the team-match record.

        Returns:
        --------
        A TeamMatch with the attributes of the team-match record.
        """
        team_match = cls(
            team=Team.from_db_response(record["team"]),
            match=Match.from_db_response(record["match"]),
            at_home=record["atHome"],
            score=record["score"],
        )
        team_match.id = record["_id"]

        return team_match

    @classmethod
    def from_raw_data(
        cls, match_data: pd.Series, match: Optional[Match] = None
    ) -> List[TeamMatch]:
        """
        Build two team-match objects from a row of raw match data.

        Params:
        -------
        match_data: A row of raw match data. Can be from fixture or match results data.

        Returns:
        --------
        A TeamMatch object.
        """
        team_matches = []

        for team_type in ["home", "away"]:
            team = Team.find_by(name=match_data[f"{team_type}_team"])
            params = {
                "team": team,
                "at_home": team_type == "home",
                "score": match_data.get(f"{team_type}_score")
                or match_data.get(f"{team_type[0]}score"),
                "match": match,
            }
            team_matches.append(cls(**params))

        return team_matches

    def create(self) -> TeamMatch:
        """Create the TeamMatch in the DB.

        Returns:
        --------
        The created TeamMatch object.
        """
        self.validate()

        query = """
            mutation(
                $teamId: ID!,
                $matchId: ID!,
                $atHome: Boolean!,
                $score: Int!
            ) {
                createTeamMatch(data: {
                    team: { connect: $teamId },
                    match: { connect: $matchId },
                    atHome: $atHome,
                    score: $score
                }) {
                    _id
                }
            }
        """
        variables = {
            "teamId": self.team and self.team.id,
            "matchId": self.match and self.match.id,
            "atHome": self.at_home,
            "score": self.score,
        }

        result = self.db_client().graphql(query, variables)
        self.id = result["createTeamMatch"]["_id"]

        return self

    @property
    def _schema(self):
        return {
            "team": {"type": "team", "check_with": self._idfulness},
            "match": {"type": "match", "check_with": self._idfulness},
            "at_home": {"type": "boolean"},
            "score": {"type": "integer", "min": 0},
        }

    @staticmethod
    def _idfulness(field, value, error):
        if value and value.id is None:
            error(field, "must have an ID")


class Match(BaseModel):
    """Data model for AFL matches."""

    def __init__(
        self,
        start_date_time: Optional[datetime] = None,
        season: Optional[int] = None,
        round_number: Optional[int] = None,
        venue: Optional[str] = None,
        winner: Optional[Team] = None,
        margin: Optional[int] = None,
        team_matches: Optional[List[TeamMatch]] = None,
    ):
        """
        Params:
        -------
        start_date_time: Timezone-aware date-time when the match is scheduled to start.
        season: The year in which the match takes place.
        round_number: Round number in which the match is played.
        venue: Name of the venue where the match is played.
        winner: The winning team.
        margin: The number of points that winner won by.
        team_matches: Models representing each team's participation in the match.
        """
        team_type = TypeDefinition("team", (Team,), ())
        Validator.types_mapping["team"] = team_type

        super().__init__(Validator)

        self.start_date_time = start_date_time
        self.season = season
        self.round_number = round_number
        self.venue = venue
        self.winner = winner
        self.margin = margin
        self.team_matches = team_matches or []
        self.id = None

        for team_match in self.team_matches:
            team_match.match = self

    @classmethod
    def filter_by_season(cls, season: Optional[int] = None) -> _MatchRecordCollection:
        """Fetch match records from the DB filtered by season year.

        Params:
        -------
        season: Filter by season year. Defaults to current year.

        Returns:
        --------
        Collection of matches.
        """
        query = """
            query($season: Int) {
                filterMatchesBySeason(season: $season) {
                    data {
                        _id
                        startDateTime
                        season
                        roundNumber
                        venue
                        winner { _id name }
                        margin
                        teamMatches {
                            data {
                                _id
                                team { _id name }
                                atHome
                                score
                            }
                        }
                    }
                }
            }
        """
        # We filter by current year, because after the season ends
        # we don't have fixtures for next season until after the start of the new year.
        variables = {"season": season or datetime.now().year}

        result = cls.db_client().graphql(query, variables)

        records = [
            cls.from_db_response(match_record)
            for match_record in result["filterMatchesBySeason"]["data"]
        ]

        return _MatchRecordCollection(records=records)

    @classmethod
    def get_or_create_from_raw_data(
        cls, match_data: Union[FixtureData, MatchData]
    ) -> Match:
        """
        Get or create a match record from a row of raw match data.

        Params:
        -------
        match_data: A row of raw match data. Can be from fixture or match results data.

        Returns:
        --------
        A Match object.
        """
        raw_date = (
            match_data["date"].to_pydatetime()
            if isinstance(match_data["date"], pd.Timestamp)
            else match_data["date"]
        )

        match_date = raw_date.astimezone(timezone.utc)

        match_params = {
            "start_date_time": match_date,
            "season": match_date.year,
            "round_number": int(match_data["round_number"]),
            "venue": match_data["venue"],
        }

        filtered_matches = Match.filter_by_season(match_date.year).filter(
            **match_params
        )

        assert len(filtered_matches) <= 1, (
            f"Expected the params {match_params} to match either one match "
            f"record or none, but received {len(filtered_matches)} match records."
        )

        if len(filtered_matches) == 1:
            return filtered_matches[0]

        return cls(**match_params).create()

    @classmethod
    def from_db_response(cls, record: Dict[str, Any]) -> Match:
        """Convert a DB record object into an instance of Match.

        Params:
        -------
        record: GraphQL response dictionary that represents the match record.

        Returns:
        --------
        A Match with the attributes of the match record.
        """
        winner = record.get("winner") and Team.from_db_response(record["winner"])

        team_match_records = (
            [] if record.get("teamMatches") is None else record["teamMatches"]["data"]
        )
        team_matches: List[TeamMatch] = [
            TeamMatch.from_db_response(team_match) for team_match in team_match_records
        ]

        match = Match(
            start_date_time=parser.parse(record["startDateTime"]),
            season=record["season"],
            round_number=record["roundNumber"],
            venue=record["venue"],
            margin=record["margin"],
            winner=winner,
            team_matches=team_matches,
        )
        match.id = record["_id"]

        return match

    def create(self) -> Match:
        """Create the match in the DB.

        Returns:
        --------
        The created match object.
        """
        self.validate()

        query = f"""
            mutation(
                {"$winnerId: ID," if self.winner else ""}
                $margin: Int,
                $startDateTime: Time!,
                $season: Int!,
                $roundNumber: Int!,
                $venue: String!,
            ) {{
                createMatch(data: {{
                    {"winner: { connect: $winnerId }," if self.winner else ""}
                    margin: $margin,
                    startDateTime: $startDateTime,
                    season: $season,
                    roundNumber: $roundNumber,
                    venue: $venue
                }}) {{
                    _id
                }}
            }}
        """

        variables = {
            "startDateTime": self._start_date_time_iso8601,
            "season": self.season,
            "roundNumber": self.round_number,
            "venue": self.venue,
            "margin": self.margin,
        }

        if self.winner:
            variables["winnerId"] = self.winner.id

        result = self.db_client().graphql(query, variables)
        self.id = result["createMatch"]["_id"]

        return self

    @property
    def _start_date_time_iso8601(self):
        if self.start_date_time is None:
            return None

        # FaunaDB's GraphQL implementation is really picky about the datetime format:
        # - Insists on 'Z' for UTC rather than permitting any timezone
        # - Requires at least 3 digits of microseconds, which Python datetimes
        #   leave blank unless they have a microsecond value. We remove microseconds,
        #   because they don't apply to match start times.
        return (
            self.start_date_time.replace(tzinfo=None, microsecond=0).isoformat()
            + ".000Z"
        )

    @property
    def _schema(self):
        return {
            "start_date_time": {"type": "datetime", "check_with": self._utcness},
            "season": {"type": "integer", "min": 1},
            "round_number": {"type": "integer", "min": 1},
            "venue": {"type": "string", "empty": False},
            "winner": {"type": "team", "nullable": True, "check_with": self._idfulness},
            "margin": {"type": "integer", "min": 0, "nullable": True},
        }

    @staticmethod
    def _utcness(field, value, error):
        if datetime.utcoffset(value) != timedelta(0):
            error(field, "must be set to the UTC timezone")

    @staticmethod
    def _idfulness(field, value, error):
        if value and value.id is None:
            error(field, "must have an ID")
