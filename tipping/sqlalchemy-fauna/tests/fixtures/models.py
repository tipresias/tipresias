"""Example model classes for use in integration tests."""

from sqlalchemy import Column, Integer, String, DateTime, Boolean, Float, orm
from sqlalchemy.sql.schema import ForeignKey, Table

from .session import Base


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
    user_foods = orm.relationship("UserFood", back_populates="user")


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
    user_foods = orm.relationship("UserFood", back_populates="food")


class UserFood(Base):
    """Fake model for join table for users and foods."""

    __tablename__ = "users_foods"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    user = orm.relationship("User", back_populates="user_foods")
    food_id = Column(Integer, ForeignKey("foods.id"))
    food = orm.relationship("Food", back_populates="user_foods")
