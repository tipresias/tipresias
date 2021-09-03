"""Module for defining the Fauna Dialect for use in SQLAlchemy."""

import os
from typing import List, Dict, Any

from sqlalchemy.engine import default
from sqlalchemy import types
from sqlalchemy.ext.compiler import compiles
from mypy_extensions import TypedDict

import sqlalchemy_fauna
from sqlalchemy_fauna.dbapi import FaunaConnection

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
    from packaging.version import Version
    from alembic.ddl import postgresql
    from alembic.ddl.base import RenameTable

    compiles(RenameTable, "fauna")(postgresql.visit_rename_table)

    if Version(alembic.__version__) >= Version("1.0.6"):
        from alembic.ddl.base import ColumnComment

        compiles(ColumnComment, "fauna")(postgresql.visit_column_comment)

    class FaunaImpl(postgresql.PostgresqlImpl):
        """Fauna implementation for use by Alembic."""

        __dialect__ = "fauna"


class FaunaExecutionContext(
    default.DefaultExecutionContext
):  # pylint: disable=abstract-method
    """Context for the execution of a query or multiple queries."""

    @property
    def rowcount(self):
        """Number of rows returned or changed by a query."""
        if hasattr(self, "_rowcount"):
            return self._rowcount
        else:
            return self.cursor.rowcount


class FaunaDialect(default.DefaultDialect):  # pylint: disable=abstract-method
    """SQLAlchemy Dialect for Fauna."""

    name = "fauna"
    scheme = os.getenv("FAUNA_SCHEME", "https")
    driver = "rest"
    execution_ctx_cls = FaunaExecutionContext

    # Pylint says this method is hidden by sqlalchemy.engine.default,
    # but all 3rd-party dialects I've looked at define 'dbapi' this way.
    @classmethod
    def dbapi(cls):  # pylint: disable=method-hidden
        """Fauna DBAPI for use in SQLAlchemy."""
        return sqlalchemy_fauna

    def do_executemany(self, cursor, statement, parameters, context=None):
        """Execute multiple statements"""
        rowcount = cursor.executemany(statement, parameters)
        if context is not None:
            context._rowcount = rowcount  # pylint: disable=protected-access

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
        column = "name_"
        query = f"SELECT {column} FROM information_schema_tables_"
        result = connection.execute(query)

        if result.rowcount == 0:
            return []

        result_keys = list(result.keys())
        name_col_idx = result_keys.index(column)

        return [row[name_col_idx] for row in result.fetchall()]

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
        info_table_name = "information_schema_columns_"
        query = f"""
            SELECT {info_table_name}.name_,
                {info_table_name}.type_,
                {info_table_name}.nullable_,
                {info_table_name}.default_
            FROM {info_table_name}
            WHERE {info_table_name}.table_name_ = '{table_name}'
        """
        result = connection.execute(query)
        result_keys = list(result.keys())

        name_col_idx = result_keys.index("name_")
        type_col_idx = result_keys.index("type_")
        nullable_col_idx = result_keys.index("nullable_")
        # Fauna strips out data with 'null' values, so we can't guarantee
        # that 'default', which has a default value of 'None', will be
        # in the result keys.
        default_col_idx = (
            result_keys.index("default_") if "default_" in result_keys else None
        )

        return [
            {
                "name": row[name_col_idx],
                "type": type_map[row[type_col_idx]],
                "nullable": row[nullable_col_idx],
                "default": None if default_col_idx is None else row[default_col_idx],
            }
            for row in result.fetchall()
        ]

    def get_pk_constraint(self, connection, table_name, schema=None, **_kwargs):
        """Get the pk constraint."""
        # Since Fauna assigns the primary key, it will always be 'id'
        return {
            "constrained_columns": ["id"],
            "name": "PRIMARY KEY",
        }

    def get_foreign_keys(self, connection, table_name, schema=None, **_kwargs):
        """Get all foreign keys."""
        info_table_name = "information_schema_indexes_"
        query = f"""
            SELECT {info_table_name}.name_,
                {info_table_name}.constrained_columns_,
                {info_table_name}.referred_table_,
                {info_table_name}.referred_columns_
            FROM {info_table_name}
            WHERE {info_table_name}.table_name_ = '{table_name}'
            AND {info_table_name}.referred_table_ IS NOT NULL
        """

        result = connection.execute(query)
        result_keys = list(result.keys())

        if len(result_keys) == 0:
            return []

        name_col_idx = result_keys.index("name_")
        constrained_columns_col_idx = result_keys.index("constrained_columns_")
        referred_columns_col_idx = result_keys.index("referred_columns_")

        return [
            {
                "name": row[name_col_idx],
                "constrained_columns": row[constrained_columns_col_idx].split(","),
                "referred_schema": None,
                "referred_table": table_name,
                "referred_columns": row[referred_columns_col_idx].split(","),
            }
            for row in result.fetchall()
        ]

    def get_check_constraints(self, connection, table_name, schema=None, **_kwargs):
        """Get check constraints."""
        return []

    def get_table_comment(self, connection, table_name, schema=None, **_kwargs):
        """Get the table comment."""
        return {"text": ""}

    def get_indexes(self, connection, table_name, schema=None, **_kwargs):
        """Get all indexes from the given table."""
        info_table_name = "information_schema_indexes_"
        query = f"""
            SELECT {info_table_name}.name_,
                {info_table_name}.column_names_,
                {info_table_name}.unique_
            FROM {info_table_name}
            WHERE {info_table_name}.table_name_ = '{table_name}'
        """

        result = connection.execute(query)
        result_keys = list(result.keys())

        if len(result_keys) == 0:
            return []

        name_col_idx = result_keys.index("name_")
        column_names_col_idx = result_keys.index("column_names_")
        unique_col_idx = result_keys.index("unique_")

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
        info_table_name = "information_schema_indexes_"
        query = f"SELECT {info_table_name}.name_, {info_table_name}.column_names_ FROM {info_table_name} WHERE {info_table_name}.table_name_ = '{table_name}' AND {info_table_name}.unique_ = TRUE"

        result = connection.execute(query)
        result_keys = list(result.keys())

        if len(result_keys) == 0:
            return []

        name_col_idx = result_keys.index("name_")
        column_names_col_idx = result_keys.index("column_names_")

        return [
            {
                "name": "UNIQUE",
                "column_names": row[column_names_col_idx].split(","),
                "duplicates_index": row[name_col_idx],
            }
            for row in result.fetchall()
        ]

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
