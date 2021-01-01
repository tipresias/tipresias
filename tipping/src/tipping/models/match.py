"""Data model for AFL matches."""

from __future__ import annotations
from typing import Optional, Dict, Any, Sequence, List, TYPE_CHECKING
from datetime import datetime, timedelta, timezone
from functools import reduce
from dateutil import parser

from cerberus import Validator, TypeDefinition
import numpy as np
import pandas as pd
from mypy_extensions import TypedDict

from .team import Team
from .base_model import BaseModel


if TYPE_CHECKING:
    from .prediction import Prediction


TeamMatchParams = TypedDict(
    "TeamMatchParams",
    {
        "team": Optional[Team],
        "at_home": Optional[bool],
        "score": Optional[int],
        "match": Optional["Match"],
    },
)

# Rough estimate, but exactitude isn't necessary here
GAME_LENGTH_HRS = 3


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
        score: Optional[int] = 0,
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
    def from_db_response(  # pylint: disable=arguments-differ
        cls,
        record: Dict[str, Any],
        match: Optional[Match] = None,
        team: Optional[Team] = None,
    ) -> TeamMatch:
        """Convert a DB record object into an instance of TeamMatch.

        Params:
        -------
        record: GraphQL response dictionary that represents the team-match record.

        Returns:
        --------
        A TeamMatch with the attributes of the team-match record.
        """
        team_match = cls(
            team=(team or Team.from_db_response(record["team"])),
            match=(match or Match.from_db_response(record["match"])),
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
        get_score = (
            lambda team_type: match_data.get(f"{team_type}_score")
            or match_data.get(f"{team_type[0]}score")
            or 0
        )
        team_matches = []

        for team_type in ["home", "away"]:
            team = Team.find_by(name=match_data[f"{team_type}_team"])
            params: TeamMatchParams = {
                "team": team,
                "at_home": team_type == "home",
                "score": get_score(team_type),
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
        self.margin = margin
        self.team_matches = team_matches or []
        self._winner = winner
        self.id = None
        self._predictions: Optional[List["Prediction"]] = None

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
    def get_or_create_from_raw_data(cls, match_data: pd.Series) -> Match:
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

        match = Match(
            start_date_time=parser.parse(record["startDateTime"]),
            season=record["season"],
            round_number=record["roundNumber"],
            venue=record["venue"],
            margin=record["margin"],
            winner=winner,
        )
        match.id = record["_id"]

        team_match_records = (
            [] if record.get("teamMatches") is None else record["teamMatches"]["data"]
        )
        team_matches: List[TeamMatch] = [
            TeamMatch.from_db_response(team_match, match=match)
            for team_match in team_match_records
        ]
        match.team_matches = team_matches

        return match

    @property
    def winner(self) -> Optional[Team]:
        """Team that won the match."""
        if self._winner is None:
            self._winner = self._calculate_winner()

        return self._winner

    @property
    def has_been_played(self) -> bool:
        """Return whether a match has been played yet."""
        if self.start_date_time is None:
            return False

        match_end_time = self.start_date_time + timedelta(hours=GAME_LENGTH_HRS)

        # We need to check the scores in case the data hasn't been updated since the
        # match was played, because as far as the data is concerned it hasn't, even though
        # the date has passed.
        return match_end_time < datetime.now(tz=timezone.utc)

    @property
    def is_draw(self) -> bool:
        """Indicate whether a match result was a draw."""
        return self._has_results and reduce(
            lambda score_x, score_y: score_x == score_y, self._match_scores
        )

    def create(self) -> Match:
        """Create the match in the DB.

        Returns:
        --------
        The created match object.
        """
        self.validate()
        self._calculate_winner()

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
    def predictions(self) -> List[Prediction]:
        """Fetch all associated prediction records from the DB.

        Returns:
        --------
        List of prediction objects.
        """
        if self._predictions is not None:
            return self._predictions

        from .prediction import Prediction  # pylint: disable=import-outside-toplevel

        query = """
            query($id: ID!) {
                findMatchByID(id: $id) {
                    predictions {
                        data {
                            _id
                            mlModel {
                                _id
                                name
                                isPrincipal
                                usedInCompetitions
                                predictionType
                            }
                            predictedWinner { _id name }
                            predictedMargin
                            predictedWinProbability
                            wasCorrect
                        }
                    }
                }
            }
        """

        variables = {"id": self.id}

        result = self.db_client().graphql(query, variables)

        self._predictions = [
            Prediction.from_db_response(prediction, match=self)
            for prediction in result["findMatchByID"]["predictions"]["data"]
        ]

        return self._predictions

    @property
    def _has_results(self):
        """Return whether a match has a final score."""
        return self.has_been_played and self._has_score

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
            "_winner": {
                "type": "team",
                "nullable": True,
                "check_with": self._idfulness,
            },
            "margin": {"type": "integer", "min": 0, "nullable": True},
            "team_matches": {"type": "list"},
            "_predictions": {"type": "list", "nullable": True},
        }

    @staticmethod
    def _utcness(field, value, error):
        if datetime.utcoffset(value) != timedelta(0):
            error(field, "must be set to the UTC timezone")

    @staticmethod
    def _idfulness(field, value, error):
        if value and value.id is None:
            error(field, "must have an ID")

    @property
    def _match_scores(self):
        return [team_match.score for team_match in self.team_matches]

    @property
    def _has_score(self):
        return any([score > 0 for score in self._match_scores])

    def _calculate_winner(self):
        """Return the record for the winning team of the match."""
        if not self.has_been_played or self.is_draw or not any(self.team_matches):
            return None

        return max(self.team_matches, key=lambda tm: tm.score).team
