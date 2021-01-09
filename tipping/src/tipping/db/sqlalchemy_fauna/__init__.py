"""Creates a Fauna Dialect for SQLAlchemy."""

from tipping.db.sqlalchemy_fauna.dbapi import connect
from tipping.db.sqlalchemy_fauna.exceptions import Error, NotSupportedError

paramstyle = "pyformat"
