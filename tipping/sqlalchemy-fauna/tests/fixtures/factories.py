"""Factories for example model classes."""

import factory
from factory.alchemy import SQLAlchemyModelFactory

from .session import Session
from .models import User


class UserFactory(SQLAlchemyModelFactory):
    """Factory class for the User data model."""

    class Meta:
        """Factory attributes for recreating the associated model's attributes."""

        model = User
        sqlalchemy_get_or_create = ("name",)
        sqlalchemy_session = Session

    name = factory.Faker("first_name")
    date_joined = factory.Faker("date_this_decade")
    age = factory.Faker("pyint")
    finger_count = factory.Faker("pyint")
    is_premium_member = factory.Faker("pybool")
    account_credit = factory.Faker("pyfloat")
    job = factory.Faker("job")
