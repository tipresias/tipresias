"""Factory classes for generating realistic DB records for tests."""

from datetime import date, datetime
import pytz

import factory
from factory.django import DjangoModelFactory
from faker import Faker
from django.utils import timezone
from django.conf import settings

from server.models import Team, Prediction, Match, MLModel, TeamMatch

FAKE = Faker()
TODAY = date.today()
JAN = 1
FIRST = 1
DEC = 12
THIRTY_FIRST = 31

N_ML_MODELS = 5
ML_MODEL_NAMES = [factory.Faker("company") for _ in range(N_ML_MODELS)]


class TeamFactory(DjangoModelFactory):
    """Factory class for the Team data model."""

    class Meta:
        """Factory attributes for recreating the associated model's attributes."""

        model = Team
        django_get_or_create = ("name",)

    name = factory.Sequence(lambda n: settings.TEAM_NAMES[n % len(settings.TEAM_NAMES)])


def fake_future_datetime(match_factory):
    """Return a realistic future datetime value for a match's start_date_time."""
    # Running tests on 28 Feb of a leap year breaks them, because the given year
    # generally won't be a leap year (e.g. 2018-2-29 doesn't exist),
    # so we retry with two days in the future (e.g. 2018-3-1).
    try:
        datetime_start = timezone.make_aware(
            datetime(match_factory.year, TODAY.month, TODAY.day + 1)
        )
    except ValueError:
        datetime_start = timezone.make_aware(
            datetime(match_factory.year, TODAY.month, TODAY.day + 2)
        )

    return FAKE.date_time_between_dates(
        datetime_start=datetime_start,
        datetime_end=timezone.make_aware(
            datetime(match_factory.year, DEC, THIRTY_FIRST)
        ),
        tzinfo=pytz.UTC,
    )


class MatchFactory(DjangoModelFactory):
    """Factory class for the Match data model."""

    class Meta:
        """Factory attributes for recreating the associated model's attributes."""

        model = Match

    start_date_time = factory.LazyAttribute(
        lambda obj: FAKE.date_time_between_dates(
            datetime_start=timezone.make_aware(datetime(obj.year, JAN, FIRST)),
            datetime_end=timezone.make_aware(datetime(obj.year, DEC, THIRTY_FIRST)),
            tzinfo=pytz.UTC,
        )
    )
    round_number = factory.Faker("pyint", min_value=1, max_value=24)
    venue = settings.VENUES[
        FAKE.pyint(min_value=0, max_value=(len(settings.VENUES) - 1))
    ]

    class Params:
        """Params for modifying the factory's default attributes."""

        year = TODAY.year
        # A lot of functionality depends on future matches for generating predictions
        future = factory.Trait(
            start_date_time=factory.LazyAttribute(fake_future_datetime)
        )


class TeamMatchFactory(DjangoModelFactory):
    """Factory class for the TeamMatch data model."""

    class Meta:
        """Factory attributes for recreating the associated model's attributes."""

        model = TeamMatch

    team = factory.SubFactory(TeamFactory)
    match = factory.SubFactory(MatchFactory)
    at_home = factory.Faker("pybool")
    score = factory.Faker("pyint", min_value=50, max_value=150)


class MLModelFactory(DjangoModelFactory):
    """Factory class for the MLModel data model."""

    class Meta:
        """Factory attributes for recreating the associated model's attributes."""

        model = MLModel

    name = factory.Faker("company")
    description = factory.Faker("paragraph", nb_sentences=4)
    filepath = "some/filepath/to/model.pkl"
    data_class_path = ""


class PredictionFactory(DjangoModelFactory):
    """Factory class for the Prediction data model."""

    class Meta:
        """Factory attributes for recreating the associated model's attributes."""

        model = Prediction

    match = factory.SubFactory(MatchFactory)
    # Can't use SubFactory for associated MLModel, because it's not realistic to have
    # one model per prediction, and in cases where there are a lot of predictions,
    # we risk duplicate model names, which is invalid
    ml_model = factory.Iterator(MLModel.objects.all())
    predicted_winner = factory.SubFactory(TeamFactory)
    predicted_margin = factory.Faker("pyint", min_value=0, max_value=50)
    # Doesn't give realistic win probabilities (i.e. between 0.5 and 1.0)
    # due to an open issue in faker: https://github.com/joke2k/faker/issues/1068
    # Since they're taking this as an opportunity to completely change the method,
    # they're going to wait for a major version rather than just permit floats...
    predicted_win_probability = factory.Faker("pyfloat", min_value=0, max_value=1)
    is_correct = factory.Faker("pybool")


class FullMatchFactory(MatchFactory):
    """
    Factory for creating a match with all associated records.

    Given the difficulty in recreating all the associations in a flexible way,
    the predictions associated with the created match are hard-coded to be two,
    which limits us to two models. So far, this has been sufficient for testing
    functionality.
    """

    prediction = factory.RelatedFactory(PredictionFactory, "match")
    prediction_two = factory.RelatedFactory(PredictionFactory, "match")

    home_team_match = factory.RelatedFactory(TeamMatchFactory, "match", at_home=True)
    away_team_match = factory.RelatedFactory(TeamMatchFactory, "match", at_home=False)
