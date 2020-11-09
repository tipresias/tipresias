"""Data model for AFL matches."""

from __future__ import annotations
from typing import Optional, List
from datetime import datetime, timedelta

from cerberus import Validator, TypeDefinition

from tipping.db.faunadb import FaunadbClient
from .team import Team


class ValidationError(Exception):
    """Exceptions for model validation violations."""


class Match:
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
        self.id = None
        self.start_date_time = start_date_time
        self.season = season
        self.round_number = round_number
        self.venue = venue
        self.winner = winner
        self.margin = margin

        team_type = TypeDefinition("team", (Team,), ())
        Validator.types_mapping["team"] = team_type
        self._validator = Validator(self._schema, purge_unknown=True)
        self._db_client = FaunadbClient()

    @classmethod
    def filter(
        cls,
        start_date_time: Optional[datetime] = None,
        season: Optional[int] = None,
        round_number: Optional[int] = None,
        venue: Optional[str] = None,
        winner: Optional[Team] = None,
        margin: Optional[int] = None,
    ) -> List[Match]:
        """Fetch matches from the DB filtered by the given param values.

        Params:
        -------
        start_date_time: Timezone-aware date-time when the match is scheduled to start.
        season: The year in which the match takes place.
        round_number: Round number in which the match is played.
        venue: Name of the venue where the match is played.
        winner: The winning team.
        margin: The number of points that winner won by.

        Returns:
        --------
        List of match objects.
        """
        query = f"""

        """

    def save(self) -> Match:
        """Save the match in the DB."""
        if not self._is_valid:
            raise ValidationError(self._errors)

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

        result = self._db_client.graphql(query, variables)

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
    def _is_valid(self):
        return self._validator.validate(self.__dict__)

    @property
    def _errors(self):
        return self._validator.errors

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
