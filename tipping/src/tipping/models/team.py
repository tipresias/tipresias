"""Data model for AFL teams."""

from __future__ import annotations
from typing import Optional, Dict, Any

from .base_model import BaseModel


class Team(BaseModel):
    """Data model for AFL teams."""

    def __init__(self, name: Optional[str] = None):
        """
        Params:
        -------
        id: ID for the database.
        name: Name of the team.
        """
        super().__init__()

        self.name = name
        self.id = None

    @classmethod
    def find_by(cls, name: str) -> Optional[Team]:
        """Fetch a team from the DB by its name.

        Params:
        -------
        name: Name of the team to be fetched.

        Returns:
        --------
        A Team with the given name.
        """
        query = """
            query($name: String!) {
                findTeamByName(name: $name) {
                    _id
                    name
                }
            }
        """
        variables = {"name": name}

        result = cls.db_client().graphql(query, variables)

        return cls.from_db_response(result["findTeamByName"])

    @classmethod
    def from_db_response(cls, record: Dict[str, Any]) -> Team:
        """Convert a DB record object into an instance of Team.

        Params:
        -------
        team_record: GraphQL response dictionary that represents the team record.

        Returns:
        --------
        A Team with the attributes of the team record.
        """
        team = Team(name=record["name"])
        team.id = record["_id"]

        return team

    def create(self) -> Team:
        """Create the team in the DB."""
        self.validate()

        query = """
            mutation($name: String!) {
                createTeam(data: { name: $name }) {
                    _id
                }
            }
        """
        variables = {"name": self.name}

        result = self.db_client().graphql(query, variables)
        self.id = result["createTeam"]["_id"]

        return self

    @property
    def _schema(self):
        return {
            "name": {
                "type": "string",
                "empty": False,
            }
        }
