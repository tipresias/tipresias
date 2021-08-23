"""Example model classes for use in integration tests."""

from sqlalchemy import Column, Integer, String, DateTime, Boolean, Float

from .session import Base


class User(Base):
    """Fake User class for use in integration tests."""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True)
    date_joined = Column(DateTime, nullable=False)
    age = Column(Integer)
    finger_count = Column(Integer, default=10)
    is_premium_member = Column(Boolean, default=False)
    account_credit = Column(Float, default=0.0)
    job = Column(String)
