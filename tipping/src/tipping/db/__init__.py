"""Manages configuration for and connections to databases."""

from sqlalchemy.dialects import registry

from tipping import settings

registry.register("fauna", "tipping.db.sqlalchemy_fauna.dialect", "FaunaDialect")
