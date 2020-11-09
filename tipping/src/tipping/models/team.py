"""Data model for AFL teams."""

from __future__ import annotations
from typing import Optional, Dict, Any
import re

from cerberus import Validator

from tipping.db.faunadb import FaunadbClient


class ValidationError(Exception):
    """Exceptions for model validation violations."""


class Team:
    """Data model for AFL teams."""

    def __init__(self, name: Optional[str] = None):  # pylint: disable=redefined-builtin
        """
        Params:
        -------
        id: ID for the database.
        name: Name of the team.
        """
        self.id = None
        self.name = name
        self._validator = Validator(self._schema, purge_unknown=True)
        self._db_client = FaunadbClient()

    @property
    def attributes(self) -> Dict[str, Any]:
        """Model attributes that get saved in the DB."""
        return {k: v for k, v in self.__dict__.items() if not re.match("_+", k)}

    def save(self) -> Team:
        """Save the team in the DB."""
        if not self._is_valid:
            raise ValidationError(self._errors)

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
    def _is_valid(self):
        return self._validator.validate(self.__dict__)

    @property
    def _errors(self):
        return self._validator.errors

    @property
    def _schema(self):
        return {
            "name": {
                "type": "string",
                "empty": False,
            }
        }
