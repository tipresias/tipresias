"""Abstract base model from which all models inherit."""

from __future__ import annotations
from typing import Dict, Any
import re

from cerberus import Validator

from tipping.db.faunadb import FaunadbClient


class ValidationError(Exception):
    """Exceptions for model validation violations."""


class BaseModel:
    """Abstract base model from which all models inherit."""

    def __init__(self, validator: Validator = Validator):
        self._validator = validator(self._schema, purge_unknown=True)
        self.id = None

    @classmethod
    def db_client(cls):
        """Create a client for querying the DB.

        Returns:
        --------
        Instance of FaunadbClient.
        """
        return FaunadbClient()

    @classmethod
    def from_db_response(cls, record: Dict[str, Any]) -> BaseModel:
        """Convert GraphQL response dict into model instance."""
        raise NotImplementedError

    @property
    def attributes(self) -> Dict[str, Any]:
        """Model attributes that get saved in the DB."""
        return {k: v for k, v in self.__dict__.items() if not re.match("_+", k)}

    def create(self):
        """Create the model in the DB."""
        raise NotImplementedError

    @property
    def _schema(self):
        raise NotImplementedError

    def _validate(self):
        if not self._is_valid:
            raise ValidationError(self._errors)

    @property
    def _is_valid(self):
        return self._validator.validate(self.__dict__)

    @property
    def _errors(self):
        return self._validator.errors
