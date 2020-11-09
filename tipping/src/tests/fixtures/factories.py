"""Factory classes for generating realistic DB records for tests."""

from datetime import datetime, timezone

import factory
import numpy as np
from faker import Faker

from tipping.models import Team, Match, TeamMatch

FAKE = Faker()

TYPICAL_MAX_ROUND = 27
REASONABLE_MIN_SCORE = 50
REASONABLE_MAX_SCORE = 150


class TeamFactory(factory.Factory):
    """Factory class for the Team data model."""

    class Meta:
        """Factory attributes for recreating the associated model's attributes."""

        model = Team

    class Params:
        """Params for modifying the factory's default attributes."""

        add_id = False

    name = factory.Faker("company")

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        model_instance = model_class(**kwargs)
        model_instance.save()
        return model_instance

    @factory.post_generation
    def build_id(obj, create, _extracted, **kwargs):  # pylint: disable=no-self-argument
        """Add fake ID when using build strategy."""
        if create or not kwargs.get("add_id"):
            return

        obj.id = (  # pylint: disable=attribute-defined-outside-init
            obj.id or FAKE.credit_card_number()
        )


class MatchFactory(factory.Factory):
    """Factory class for the Match data model."""

    class Meta:
        """Factory attributes for recreating the associated model's attributes."""

        model = Match

    class Params:
        """Params for modifying the factory's default attributes."""

        add_id = False

    start_date_time = factory.Faker("date_time", tzinfo=timezone.utc)
    season = factory.Faker("pyint")
    round_number = factory.LazyAttribute(
        lambda _match: np.random.randint(1, TYPICAL_MAX_ROUND + 1)
    )
    venue = factory.Faker("street_name")
    winner = factory.LazyAttribute(
        lambda _match: np.random.choice([TeamFactory.build(), None])
    )
    margin = factory.LazyAttribute(
        lambda _match: np.random.choice(
            [np.random.randint(0, REASONABLE_MAX_SCORE - REASONABLE_MIN_SCORE), None]
        )
    )

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        model_instance = model_class(**kwargs)
        model_instance.save()
        return model_instance

    @factory.post_generation
    def build_id(obj, create, _extracted, **kwargs):  # pylint: disable=no-self-argument
        """Add fake ID when using build strategy."""
        if create or not kwargs.get("add_id"):
            return

        obj.id = (  # pylint: disable=attribute-defined-outside-init
            obj.id or FAKE.credit_card_number()
        )


class TeamMatchFactory(factory.Factory):
    """Factory class for the TeamMatch data model."""

    class Meta:
        """Factory attributes for recreating the associated model's attributes."""

        model = TeamMatch

    class Params:
        """Params for modifying the factory's default attributes."""

        add_id = False

    team = TeamFactory.build()
    match = MatchFactory.build()
    at_home = factory.Faker("pybool")
    score = factory.LazyAttribute(
        lambda team_match: np.random.randint(REASONABLE_MIN_SCORE, REASONABLE_MAX_SCORE)
        if team_match.match.start_date_time < datetime.now(tz=timezone.utc)
        else 0
    )

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        model_instance = model_class(**kwargs)
        model_instance.save()
        return model_instance

    @factory.post_generation
    def build_id(obj, create, _extracted, **kwargs):  # pylint: disable=no-self-argument
        """Add fake ID when using build strategy."""
        if create or not kwargs.get("add_id"):
            return

        obj.id = (  # pylint: disable=attribute-defined-outside-init
            obj.id or FAKE.credit_card_number()
        )
