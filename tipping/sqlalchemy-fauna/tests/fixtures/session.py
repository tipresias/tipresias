"""Base SQLAlchemy session for use in integration tests."""

from sqlalchemy.orm import scoped_session, session
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()
Session = scoped_session(session.sessionmaker())
