"""Data model for the connection between matches and teams."""

from __future__ import annotations
from typing import Optional

from cerberus import Validator, TypeDefinition

from .team import Team
from .match import Match
from .base_model import BaseModel


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

    def create(self) -> TeamMatch:
        """Create the TeamMatch in the DB."""
        self._validate()

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
