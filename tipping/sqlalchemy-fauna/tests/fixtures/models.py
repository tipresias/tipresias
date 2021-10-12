"""Example model classes for use in integration tests."""

from sqlalchemy import Column, Integer, String, DateTime, Boolean, Float, orm
from sqlalchemy.sql.schema import ForeignKey, Table

from .session import Base

users_foods_table = Table(
    "users_foods",
    Base.metadata,
    Column("user_id", ForeignKey("users.id")),
    Column("food_id", ForeignKey("foods.id")),
)


class User(Base):
    """Fake User model for use in integration tests."""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True)
    date_joined = Column(DateTime, nullable=False)
    age = Column(Integer)
    finger_count = Column(Integer, default=10)
    is_premium_member = Column(Boolean, default=False)
    account_credit = Column(Float, default=0.0)
    job = Column(String)
    children = orm.relationship("Child", back_populates="user")
    favorite_foods = orm.relationship(
        "Food", secondary=users_foods_table, back_populates="eaters"
    )


class Child(Base):
    """Fake Child model for use in integration tests."""

    __tablename__ = "children"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    user = orm.relationship("User", back_populates="children")
    name = Column(String, unique=True)
    game = Column(String)


class Food(Base):
    """Fake Food model for use in integration tests."""

    __tablename__ = "foods"

    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True)
    flavor = Column(String)
    eaters = orm.relationship(
        "User", secondary=users_foods_table, back_populates="favorite_foods"
    )
