"""Factory classes for generating realistic DB records for tests."""

from datetime import date, datetime
import pytz

import factory
from factory.django import DjangoModelFactory
from faker import Faker
from django.utils import timezone
from django.conf import settings
import numpy as np

from server.models import Team, Prediction, Match, MLModel, TeamMatch
from server.models.ml_model import PredictionType

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

    # TODO: Make start_date_time increment in sync with round_number,
    # because sometimes fake data will have matches with higher round numbers,
    # but earlier dates, which can cause test to fail, depending on how
    # we're sorting data.
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
    is_principle = False
    used_in_competitions = False


class PredictionFactory(DjangoModelFactory):
    """Factory class for the Prediction data model."""

    class Meta:
        """Factory attributes for recreating the associated model's attributes."""

        model = Prediction

    class Params:
        """
        Params for modifying the factory's default attributes.

        Params:
        -------
        force_correct: A factory trait that, when present, forces the predicted_winner
            to equal the actual match winner. We sometimes need this for tests
            that check prediction metric calculations.
        """

        force_correct = factory.Trait(
            predicted_winner=factory.LazyAttribute(
                lambda pred: pred.match.teammatch_set.order_by("-score").first().team
            )
        )

    match = factory.SubFactory(MatchFactory)
    # Can't use SubFactory for associated MLModel, because it's not realistic to have
    # one model per prediction, and in cases where there are a lot of predictions,
    # we risk duplicate model names, which is invalid
    ml_model = factory.Iterator(MLModel.objects.all())
    # Have to make sure we get a team from the associated match
    # for realistic prediction metrics
    predicted_winner = factory.LazyAttribute(
        lambda pred: pred.match.teammatch_set.all()[np.random.randint(0, 2)].team
    )
    predicted_margin = factory.LazyAttribute(
        lambda pred: FAKE.pyint(min_value=0, max_value=50)
        if pred.ml_model.prediction_type == PredictionType.MARGIN
        else None
    )
    # Doesn't give realistic win probabilities (i.e. between 0.5 and 1.0)
    # due to an open issue in faker: https://github.com/joke2k/faker/issues/1068
    # Since they're taking this as an opportunity to completely change the method,
    # they're going to wait for a major version rather than just permit floats...
    predicted_win_probability = factory.LazyAttribute(
        lambda pred: FAKE.pyfloat(min_value=0, max_value=1)
        if pred.ml_model.prediction_type == PredictionType.WIN_PROBABILITY
        else None
    )
    is_correct = factory.LazyAttribute(
        lambda pred: (
            pred.match.teammatch_set.order_by("-score").first().team
            == pred.predicted_winner
        )
    )


class FullMatchFactory(MatchFactory):
    """
    Factory for creating a match with all associated records.

    Given the difficulty in recreating all the associations in a flexible way,
    the predictions associated with the created match are hard-coded to be two,
    which limits us to two models. So far, this has been sufficient for testing
    functionality.
    """

    class Params:
        """
        Params for modifying the factory's default attributes.

        Params:
        -------
        with_predictions: A factory trait that, when present, creates ML model
            predictions associated with the match.
        """

        with_predictions = factory.Trait(
            prediction=factory.RelatedFactory(PredictionFactory, "match"),
            prediction_two=factory.RelatedFactory(PredictionFactory, "match"),
        )

    # TeamMatchFactory calls must come before PredictionFactory calls,
    # so predictions can refer to associated teams for predicted_winner.
    home_team_match = factory.RelatedFactory(TeamMatchFactory, "match", at_home=True)
    away_team_match = factory.RelatedFactory(TeamMatchFactory, "match", at_home=False)
