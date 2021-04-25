"""Creates a Fauna Dialect for SQLAlchemy."""

from tipping.sqlalchemy_fauna.dbapi import connect
from tipping.sqlalchemy_fauna.exceptions import Error, NotSupportedError

paramstyle = "pyformat"
