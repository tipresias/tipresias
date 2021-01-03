"""Module for defining the Fauna Dialect for use in SQLAlchemy."""

from typing import List, Dict, Any

from sqlalchemy.engine import default
from sqlalchemy import types
from mypy_extensions import TypedDict

from tipping.settings import IS_PRODUCTION
from tipping.db import sqlalchemy_fauna
from tipping.db.sqlalchemy_fauna.dbapi import FaunaConnection

ColumnName = TypedDict(
    "ColumnName",
    {
        "name": str,
        "type": Any,
        "nullable": bool,
        "default": Any,
    },
)


type_map = {
    "string": types.String,
    "number": types.Numeric,
    "boolean": types.Boolean,
    "date": types.DATE,
    "datetime": types.DATETIME,
    "timeofday": types.TIME,
}


class FaunaDialect(default.DefaultDialect):  # pylint: disable=abstract-method
    """SQLAlchemy Dialect for Fauna."""

    name = "fauna"
    scheme = "https" if IS_PRODUCTION else "http"
    driver = "rest"

    # Pylint says this method is hidden by sqlalchemy.engine.default,
    # but all 3rd-party dialects I've looked at define 'dbapi' this way.
    @classmethod
    def dbapi(cls):  # pylint: disable=method-hidden
        """Fauna DBAPI for use in SQLAlchemy."""
        return sqlalchemy_fauna

    def create_connect_args(self, url):
        """Transform the database URL into connection kwargs."""
        opts = url.translate_connect_args()
        opts.update(url.query)
        return [[], {**opts, "scheme": self.scheme}]

    def get_schema_names(self, _connection, **_kwargs) -> List[str]:
        """Return the database schema names.

        This is just a blank string, because Fauna doesn't have schema names.
        """
        return [""]

    def has_table(
        self, connection: FaunaConnection, table_name: str, schema=None
    ) -> bool:
        """Check whether the database has the given table."""
        return table_name in self.get_table_names(connection, schema)

    def get_table_names(
        self, connection: FaunaConnection, schema=None, **kwargs
    ) -> List[str]:
        """Get the names of all Fauna collections"""
        raise Exception("TBI")

    def get_view_names(self, connection, schema=None, **_kwargs) -> List[str]:
        """Get the names of views."""
        return []

    def get_table_options(
        self,
        _connection,
        _table_name,
        schema=None,  # pylint: disable=unused-argument
        **_kwargs
    ) -> Dict[str, Any]:
        """Get table options."""
        return {}

    def get_columns(
        self, connection: FaunaConnection, table_name: str, schema=None, **_kwargs
    ) -> List[ColumnName]:
        """Get all column names in the given table."""
        raise Exception("TBI")

        query = "some query"  # pylint: disable=unreachable
        result = connection.execute(query)
        return [
            {
                "name": col[0],
                "type": type_map[col],
                "nullable": True,
                "default": None,
            }
            for col in result[0]
        ]

    def get_pk_constraint(self, _connection, table_name, schema=None, **_kwargs):
        """Get the pk constraint."""
        return {"constrained_columns": [], "name": None}

    def get_foreign_keys(self, connection, table_name, schema=None, **_kwargs):
        """Get all foreign keys."""
        return []

    def get_check_constraints(self, connection, table_name, schema=None, **_kwargs):
        """Get check constraints."""
        return []

    def get_table_comment(self, connection, table_name, schema=None, **_kwargs):
        """Get the table comment."""
        return {"text": ""}

    def get_indexes(self, connection, table_name, schema=None, **_kwargs):
        """Get all indexes from the given table."""
        return []

    def get_unique_constraints(self, connection, table_name, schema=None, **_kwargs):
        """Get the unique constraints for the given table."""
        return []

    def get_view_definition(self, connection, view_name, schema=None, **kwargs):
        """Get the view definition."""

    def do_rollback(self, dbapi_connection):
        """Rollback a transaction."""
        # TODO: I think Fauna has transactions, because FQL has an 'Abort' function
        # for terminating them

    def _check_unicode_returns(self, connection, additional_tests=None):
        return True

    def _check_unicode_description(self, connection):
        return True
