"""Creates a Fauna Dialect for SQLAlchemy."""

from sqlalchemy_fauna.dbapi import connect
from sqlalchemy_fauna.exceptions import Error, NotSupportedError

paramstyle = "pyformat"
