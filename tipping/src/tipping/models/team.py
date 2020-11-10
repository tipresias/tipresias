"""Data model for AFL teams."""

from __future__ import annotations
from typing import Optional

from .base_model import BaseModel


class Team(BaseModel):
    """Data model for AFL teams."""

    def __init__(self, name: Optional[str] = None):  # pylint: disable=redefined-builtin
        """
        Params:
        -------
        id: ID for the database.
        name: Name of the team.
        """
        super().__init__()

        self.name = name

    def create(self) -> Team:
        """Create the team in the DB."""
        self._validate()

        query = """
            mutation($name: String!) {
                createTeam(data: { name: $name }) {
                    _id
                }
            }
        """
        variables = {"name": self.name}

        result = self._db_client.graphql(query, variables)
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
