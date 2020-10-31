"""Factory classes for generating realistic DB records for tests."""

from datetime import date, datetime, timedelta
import math
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
MAR = 3
ONE_WEEK = 7
SIX_MONTHS_IN_WEEKS = 26

# A full round with all teams playing each other currently has 9 matches.
TYPICAL_N_MATCHES_PER_ROUND = 9
# A typical regular season has 24 rounds, so we set that as the limit
# to keep round number realistic.
N_ROUNDS_PER_REGULAR_SEASON = 24

N_ML_MODELS = 5
ML_MODEL_NAMES = [factory.Faker("company") for _ in range(N_ML_MODELS)]


class TeamFactory(DjangoModelFactory):
    """Factory class for the Team data model."""

    class Meta:
        """Factory attributes for recreating the associated model's attributes."""

        model = Team
        django_get_or_create = ("name",)

    name = factory.Sequence(lambda n: settings.TEAM_NAMES[n % len(settings.TEAM_NAMES)])


def _fake_datetime(match_factory, n, start_month_day=(MAR, FIRST)) -> datetime:
    round_week_delta = timedelta(days=ONE_WEEK)

    # Since we create match records per year, we don't want want dates running
    # into the next year.
    max_datetime = timezone.make_aware(datetime(match_factory.year, DEC, THIRTY_FIRST))
    now_for_factory = timezone.make_aware(
        datetime(match_factory.year, *start_month_day)
    )

    # We cycle through six month periods (or however many weeks are left in the year,
    # whichever is less), because the sequence doesn't reset between tests
    # and eventually hits the end of the year for every test, resulting in duplicate
    # venue/date combinations that raise validation errors.
    n_weeks_left_in_year = round((max_datetime - now_for_factory).days / ONE_WEEK)
    n_weeks_left_in_season = min([n_weeks_left_in_year, SIX_MONTHS_IN_WEEKS])
    start_round_week_delta = round_week_delta * (
        math.ceil(n / TYPICAL_N_MATCHES_PER_ROUND) % n_weeks_left_in_season
    )

    try:
        # The AFL season typically starts in March
        datetime_start = now_for_factory + start_round_week_delta
    except ValueError:
        # Trying to create a datetime for 29 Feb in a non-leap year raises an error,
        # (e.g. 2018-2-29 doesn't exist), so we retry with an extra day in the future
        # (e.g. 2018-3-1).
        datetime_start = (
            timezone.make_aware(datetime(match_factory.year, MAR, FIRST))
            + start_round_week_delta
            + timedelta(days=1)
        )

    try:
        # Rounds last about a week, so that's how big we make our date range per round.
        datetime_end = datetime_start + round_week_delta
    except ValueError:
        # Trying to create a datetime for 29 Feb in a non-leap year raises an error,
        # (e.g. 2018-2-29 doesn't exist), so we retry with an extra day in the future
        # (e.g. 2018-3-1).
        datetime_end = datetime_start + round_week_delta + timedelta(days=1)

    return FAKE.date_time_between_dates(
        datetime_start=min(datetime_start, max_datetime),
        datetime_end=min(datetime_end, max_datetime),
        tzinfo=pytz.UTC,
    )


def _fake_future_datetime(match_factory, n) -> datetime:
    """Return a realistic future datetime value for a match's start_date_time."""
    if TODAY.month == 12 and TODAY.day == 31:
        match_factory.year = match_factory.year + 1

    tomorrow = TODAY + timedelta(days=1)

    return _fake_datetime(
        match_factory, n, start_month_day=(tomorrow.month, tomorrow.day)
    )


class MatchFactory(DjangoModelFactory):
    """Factory class for the Match data model."""

    class Meta:
        """Factory attributes for recreating the associated model's attributes."""

        model = Match

    start_date_time = factory.LazyAttributeSequence(_fake_datetime)
    round_number = factory.Sequence(
        lambda n: math.ceil((n + 1) / TYPICAL_N_MATCHES_PER_ROUND)
        % N_ROUNDS_PER_REGULAR_SEASON
    )
    venue = factory.LazyFunction(
        lambda: settings.VENUES[
            FAKE.pyint(min_value=0, max_value=(len(settings.VENUES) - 1))
        ]
    )

    class Params:
        """Params for modifying the factory's default attributes."""

        year = TODAY.year
        # A lot of functionality depends on future matches for generating predictions
        future = factory.Trait(
            start_date_time=factory.LazyAttributeSequence(_fake_future_datetime)
        )


class TeamMatchFactory(DjangoModelFactory):
    """Factory class for the TeamMatch data model."""

    class Meta:
        """Factory attributes for recreating the associated model's attributes."""

        model = TeamMatch

    team = factory.SubFactory(TeamFactory)
    match = factory.SubFactory(MatchFactory)
    at_home = factory.Faker("pybool")
    score = factory.LazyAttribute(
        lambda team_match: FAKE.pyint(min_value=50, max_value=150)
        if team_match.match.start_date_time < timezone.now()
        else 0
    )

    @factory.post_generation
    def save_match_result(
        obj, _create, _extracted, **_kwargs
    ):  # pylint: disable=no-self-argument
        """Update associated match with result."""
        obj.match._save_result()  # pylint: disable=protected-access


class MLModelFactory(DjangoModelFactory):
    """Factory class for the MLModel data model."""

    class Meta:
        """Factory attributes for recreating the associated model's attributes."""

        model = MLModel

    name = factory.Faker("company")
    description = factory.Faker("paragraph", nb_sentences=4)
    is_principal = False
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
                lambda pred: max(
                    pred.match.teammatch_set.all(), key=lambda pred: pred.score
                ).team
            )
        )

        force_incorrect = factory.Trait(
            predicted_winner=factory.LazyAttribute(
                lambda pred: min(
                    pred.match.teammatch_set.all(), key=lambda pred: pred.score
                ).team
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
        lambda pred: np.random.random() * 50
        if pred.ml_model.prediction_type == PredictionType.MARGIN
        else None
    )
    # Doesn't give realistic win probabilities (i.e. between 0.5 and 1.0)
    # due to an open issue in faker: https://github.com/joke2k/faker/issues/1068
    # Since they're taking this as an opportunity to completely change the method,
    # they're going to wait for a major version rather than just permit floats...
    predicted_win_probability = factory.LazyAttribute(
        lambda pred: np.random.uniform(0.5, 1.0)
        if pred.ml_model.prediction_type == PredictionType.WIN_PROBABILITY
        else None
    )
    is_correct = factory.LazyAttribute(
        lambda pred: (
            None
            if pred.match.start_date_time > timezone.now()
            else pred.match.teammatch_set.order_by("-score").first().team
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
