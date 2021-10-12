"""Factories for example model classes."""

import factory
from factory.alchemy import SQLAlchemyModelFactory
from faker import Faker

from .session import Session
from .models import Food, User, Child


Fake = Faker()


class UserFactory(SQLAlchemyModelFactory):
    """Factory class for the User data model."""

    class Meta:
        """Factory attributes for recreating the associated model's attributes."""

        model = User
        sqlalchemy_session = Session

    name = factory.Sequence(lambda n: f"{Fake.first_name()} {n}")
    date_joined = factory.Faker("date_this_decade")
    age = factory.Faker("pyint")
    finger_count = factory.Faker("pyint")
    is_premium_member = factory.Faker("pybool")
    account_credit = factory.Faker("pyfloat")
    job = factory.Faker("job")


class ChildFactory(SQLAlchemyModelFactory):
    """Factory class for the Child data model."""

    class Meta:
        """Factory attributes for recreating the associated model's attributes."""

        model = Child
        sqlalchemy_session = Session

    name = factory.Sequence(lambda n: f"{Fake.first_name()} {n}")
    user = factory.SubFactory(UserFactory)
    game = factory.Faker("bs")


class FoodFactory(SQLAlchemyModelFactory):
    """Factory class for the Food data model."""

    class Meta:
        """Factory attributes for recreating the associated model's attributes."""

        model = Food
        sqlalchemy_session = Session

    name = factory.Sequence(lambda n: f"{Fake.word()} {n}")
    flavor = factory.Faker("bs")
