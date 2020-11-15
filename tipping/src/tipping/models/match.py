"""Data model for AFL matches."""

from __future__ import annotations
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from dateutil import parser

from cerberus import Validator, TypeDefinition
import numpy as np

from .team import Team
from .base_model import BaseModel


class _MatchRecordCollection:
    """Collection of match match objects associated with records in FaunaDB."""

    def __init__(self, records: List[Optional[Match]]):
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
    def from_db_response(cls, record: Optional[Dict[str, Any]]) -> Optional[Match]:
        """Convert a DB record object into an instance of Match.

        Params:
        -------
        record: GraphQL response dictionary that represents the match record.

        Returns:
        --------
        A Match with the attributes of the match record.
        """
        if record is None:
            return None

        match = Match(
            start_date_time=parser.parse(record["startDateTime"]),
            season=record["season"],
            round_number=record["roundNumber"],
            venue=record["venue"],
            margin=record["margin"],
            winner=Team.from_db_response(record["winner"]),
        )
        match.id = record["_id"]

        return match

    def create(self) -> Match:
        """Create the match in the DB.

        Returns:
        --------
        The created match object.
        """
        self._validate()

        query = f"""
            mutation(
                {"$winnerId: ID," if self.winner else ""}
                $margin: Int,
                $startDateTime: Time!,
                $season: Int!,
                $roundNumber: Int!,
                $venue: String!
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
