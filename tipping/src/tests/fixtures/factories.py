# pylint: disable=attribute-defined-outside-init,no-self-argument
"""Factory classes for generating realistic DB records for tests."""

from __future__ import annotations
from datetime import datetime, timezone, timedelta, date
import math

import factory
from faker import Faker
import numpy as np

from tipping.models import Team, Match, TeamMatch, MLModel, Prediction
from tipping.models.base_model import BaseModel
from tipping import settings

FAKE = Faker()

TODAY = date.today()
JAN = 1
FIRST = 1
DEC = 12
THIRTY_FIRST = 31
MAR = 3
ONE_WEEK = 7
SIX_MONTHS_IN_WEEKS = 26

REASONABLE_MIN_SCORE = 50
REASONABLE_MAX_SCORE = 150
# A full round with all teams playing each other currently has 9 matches.
TYPICAL_N_MATCHES_PER_ROUND = 9
# A typical regular season has 24 rounds, so we set that as the limit
# to keep round number realistic.
N_ROUNDS_PER_REGULAR_SEASON = 24


def _fake_datetime(match_factory, n, start_month=MAR, start_day=FIRST) -> datetime:
    round_week_delta = timedelta(days=ONE_WEEK)

    # Since we create match records per year, we don't want want dates running
    # into the next year.
    max_datetime = datetime(
        match_factory.season_param, DEC, THIRTY_FIRST, tzinfo=timezone.utc
    )
    now_for_factory = datetime(
        match_factory.season_param, start_month, start_day, tzinfo=timezone.utc
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
            datetime(match_factory.season_param, MAR, FIRST, tzinfo=timezone.utc)
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
        tzinfo=timezone.utc,
    )


def _fake_future_datetime(match_factory, n) -> datetime:
    """Return a realistic future datetime value for a match's start_date_time."""
    if TODAY.month == DEC and TODAY.day == THIRTY_FIRST:
        match_factory.season_param = match_factory.season_param + 1

    tomorrow = TODAY + timedelta(days=1)

    return _fake_datetime(
        match_factory, n, start_month=tomorrow.month, start_day=tomorrow.day
    )


class TippingFactory(factory.Factory):
    """Abstract factory class with functionality specific to the Tipping service."""

    class Params:
        """Params for modifying the factory's default attributes."""

    @factory.post_generation
    def add_id(obj, create, extracted, **_kwargs):
        """Add fake ID when using build strategy."""
        if create or not extracted:
            return

        obj.id = obj.id or FAKE.credit_card_number()

        # It's a huge pain trying to make sure all associated models get IDs,
        # because sometimes they aren't generated via RelatedFactory, so can't receive
        # nested params, so we assume that if the given model should have an ID,
        # all the rest should as well.
        for attr, attr_value in obj.attributes.items():
            if not isinstance(attr_value, BaseModel):
                continue

            associated_model = getattr(obj, attr)
            setattr(associated_model, "id", FAKE.credit_card_number())


class TeamFactory(TippingFactory):
    """Factory class for the Team data model."""

    class Meta:
        """Factory attributes for recreating the associated model's attributes."""

        model = Team

    name = factory.Faker("company")

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        model_instance = model_class(**kwargs)
        model_instance.create()
        return model_instance


class MLModelFactory(TippingFactory):
    """Factory class for the MLModel data model."""

    class Meta:
        """Factory attributes for recreating the associated model's attributes."""

        model = MLModel

    name = factory.Faker("company")
    is_principal = False
    used_in_competitions = False
    prediction_type = factory.LazyFunction(
        lambda: np.random.choice(MLModel.PREDICTION_TYPES)
    )

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        model_instance = model_class(**kwargs)
        model_instance.create()
        return model_instance


class MatchFactory(TippingFactory):
    """Factory class for the Match data model."""

    class Meta:
        """Factory attributes for recreating the associated model's attributes."""

        model = Match

    class Params:
        """Params for modifying the factory's default attributes."""

        season_param = TODAY.year
        # A lot of functionality depends on future matches for generating predictions
        future = factory.Trait(
            start_date_time=factory.LazyAttributeSequence(_fake_future_datetime)
        )

    start_date_time = factory.LazyAttributeSequence(_fake_datetime)
    season = factory.SelfAttribute("start_date_time.year")
    round_number = factory.Sequence(
        lambda n: math.ceil((n + 1) / TYPICAL_N_MATCHES_PER_ROUND)
        % N_ROUNDS_PER_REGULAR_SEASON
    )
    venue = factory.LazyFunction(lambda: np.random.choice(settings.VENUES))
    team_matches = factory.RelatedFactoryList(
        "tests.fixtures.factories.TeamMatchFactory",
        factory_related_name="match",
        size=2,
    )

    @factory.post_generation
    def calculate_winner(obj, _create, _extracted, **_kwargs):
        "Assign correct winner to the given match."
        obj.winner = obj._calculate_winner()

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        model_instance = model_class(**kwargs)

        if model_instance.winner and model_instance.winner.id is None:
            model_instance.winner.create()

        for team_match in model_instance.team_matches:
            if team_match.id is None:
                team_match.create()

        model_instance.create()
        return model_instance


class TeamMatchFactory(TippingFactory):
    """Factory class for the TeamMatch data model."""

    class Meta:
        """Factory attributes for recreating the associated model's attributes."""

        model = TeamMatch

    team = factory.SubFactory(TeamFactory)
    match = factory.SubFactory(MatchFactory)
    at_home = factory.LazyAttributeSequence(lambda _, n: bool(n % 2))
    score = factory.LazyAttribute(
        lambda team_match: FAKE.pyint(min_value=50, max_value=150)
        if team_match.match.start_date_time < datetime.now(tz=timezone.utc)
        else 0
    )

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        model_instance = model_class(**kwargs)

        if model_instance.team.id is None:
            model_instance.team.create()

        if model_instance.match.id is None:
            model_instance.match.create()

        model_instance.create()
        return model_instance


class PredictionFactory(TippingFactory):
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
        force_incorrect: A factory trait that, when present, forces the predicted_winner
            to not equal the actual match winner.
        """

        force_correct = factory.Trait(
            predicted_winner=factory.LazyAttribute(
                lambda pred: max(
                    pred.match.team_matches, key=lambda pred: pred.score
                ).team
            )
        )

        force_incorrect = factory.Trait(
            predicted_winner=factory.LazyAttribute(
                lambda pred: min(
                    pred.match.team_matches, key=lambda pred: pred.score
                ).team
            )
        )

        ml_models = [MLModelFactory.build() for _ in range(5)]

    match = factory.SubFactory(MatchFactory)
    # Can't use SubFactory for associated MLModel, because it's not realistic to have
    # one prediction per model, and in cases where there are a lot of predictions,
    # we risk duplicate model names, which is invalid
    ml_model = factory.LazyAttributeSequence(
        lambda ml_model_factory, n: ml_model_factory.ml_models[
            n % len(ml_model_factory.ml_models)
        ]
    )
    # Have to make sure we get a team from the associated match
    # for realistic prediction metrics
    predicted_winner = factory.LazyAttribute(
        lambda pred: pred.match.team_matches[np.random.randint(0, 2)].team
    )
    predicted_margin = factory.LazyAttribute(
        lambda pred: np.random.random() * 50
        if pred.ml_model.prediction_type == "margin"
        else None
    )
    predicted_win_probability = factory.LazyAttribute(
        lambda pred: np.random.uniform(0.5, 1.0)
        if pred.ml_model.prediction_type == "win_probability"
        else None
    )
    was_correct = factory.LazyAttribute(
        lambda pred: (
            None
            if pred.match.start_date_time > datetime.now(tz=timezone.utc)
            else sorted(pred.match.team_matches, key=lambda tm: tm.score)[-1].team
            == pred.predicted_winner
        )
    )

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        model_instance = model_class(**kwargs)

        if (
            model_instance.predicted_winner
            and model_instance.predicted_winner.id is None
        ):
            model_instance.predicted_winner.create()

        if model_instance.match and model_instance.match.id is None:
            model_instance.match.create()

        if model_instance.ml_model and model_instance.ml_model.id is None:
            model_instance.ml_model.create()

        model_instance.create()
        return model_instance
