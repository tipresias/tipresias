"""Manages configuration for and connections to databases."""

from sqlalchemy.dialects import registry

registry.register("fauna", "tipping.db.sqlalchemy_fauna.dialect", "FaunaDialect")
