"""Module for defining the Fauna Dialect for use in SQLAlchemy."""

from typing import List, Dict, Any
from packaging.version import Version

from sqlalchemy.engine import default
from sqlalchemy import types
from sqlalchemy.ext.compiler import compiles
from mypy_extensions import TypedDict

from tipping.settings import IS_PRODUCTION
from tipping import sqlalchemy_fauna
from tipping.sqlalchemy_fauna.dbapi import FaunaConnection

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
    "String": types.String,
    "Float": types.Float,
    "Integer": types.Integer,
    "Boolean": types.Boolean,
    "Date": types.DATE,
    "TimeStamp": types.DATETIME,
}

# The below is copy/pasted from https://github.com/sqlalchemy-redshift/sqlalchemy-redshift
# (file sqlalchemy_redshift/dialect.py) to enable use of alembic
# with a 3rd-party SQLAlchemy Dialect
try:
    import alembic
except ImportError:
    pass
else:
    from alembic.ddl import postgresql

    from alembic.ddl.base import RenameTable

    compiles(RenameTable, "fauna")(postgresql.visit_rename_table)

    if Version(alembic.__version__) >= Version("1.0.6"):
        from alembic.ddl.base import ColumnComment

        compiles(ColumnComment, "fauna")(postgresql.visit_column_comment)

    class FaunaImpl(postgresql.PostgresqlImpl):
        """Fauna implementation for use by Alembic."""

        __dialect__ = "fauna"


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
        self, connection: FaunaConnection, table_name: str, schema=None, **kw
    ) -> bool:
        """Check whether the database has the given table."""
        return table_name in self.get_table_names(connection, schema)

    def get_table_names(
        self, connection: FaunaConnection, schema=None, **_kwargs
    ) -> List[str]:
        """Get the names of all Fauna collections"""
        query = "SELECT * FROM INFORMATION_SCHEMA.TABLES;"
        result = connection.execute(query)

        if result.rowcount == 0:
            return []

        result_keys = list(result.keys())
        id_col_idx = result_keys.index("id")

        return [row[id_col_idx] for row in result.fetchall()]

    def get_view_names(self, connection, schema=None, **_kwargs) -> List[str]:
        """Get the names of views."""
        return []

    def get_table_options(
        self,
        _connection,
        _table_name,
        schema=None,  # pylint: disable=unused-argument
        **_kwargs,
    ) -> Dict[str, Any]:
        """Get table options."""
        return {}

    def get_columns(
        self, connection: FaunaConnection, table_name: str, schema=None, **_kwargs
    ) -> List[ColumnName]:
        """Get all columns in the given table."""
        query = f"""
            SELECT * FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_NAME = '{table_name}';
        """
        result = connection.execute(query)

        result_keys = list(result.keys())

        name_col_idx = result_keys.index("name")
        type_col_idx = result_keys.index("type")
        not_null_col_idx = result_keys.index("not_null")
        # Fauna strips out data with 'null' values, so we can't guarantee
        # that 'default', which has a default value of 'None', will be
        # in the result keys.
        default_col_idx = (
            result_keys.index("default") if "default" in result_keys else None
        )

        return [
            {
                "name": row[name_col_idx],
                "type": type_map[row[type_col_idx]],
                "nullable": not row[not_null_col_idx],
                "default": None if default_col_idx is None else row[default_col_idx],
            }
            for row in result.fetchall()
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
        query = f"""
            SELECT * FROM INFORMATION_SCHEMA.CONSTRAINT_TABLE_USAGE
            WHERE TABLE_NAME = '{table_name}';
        """

        result = connection.execute(query)

        result_keys = list(result.keys())

        if len(result_keys) == 0:
            return []

        name_col_idx = result_keys.index("name")
        column_names_col_idx = result_keys.index("column_names")
        unique_col_idx = result_keys.index("unique")

        return [
            {
                "name": row[name_col_idx],
                "column_names": row[column_names_col_idx].split(","),
                "unique": row[unique_col_idx],
            }
            for row in result.fetchall()
        ]

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
