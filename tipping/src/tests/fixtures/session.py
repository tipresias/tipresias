"""Base SQLAlchemy session for use in integration tests."""

from sqlalchemy.orm import scoped_session, session

Session = scoped_session(session.sessionmaker())
