"""Factory classes for generating realistic DB records for tests."""

from datetime import datetime, timezone, timedelta, date
import math

import factory
import numpy as np
from faker import Faker

from tipping.models import Team, Match, TeamMatch
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

        add_id = False

    @factory.post_generation
    def build_id(obj, create, _extracted, **kwargs):  # pylint: disable=no-self-argument
        """Add fake ID when using build strategy."""
        if create or not kwargs.get("add_id"):
            return

        obj.id = (  # pylint: disable=attribute-defined-outside-init
            obj.id or FAKE.credit_card_number()
        )


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


class MatchFactory(TippingFactory):
    """Factory class for the Match data model."""

    class Meta:
        """Factory attributes for recreating the associated model's attributes."""

        model = Match

    start_date_time = factory.LazyAttributeSequence(_fake_datetime)
    season = factory.SelfAttribute("start_date_time.year")
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

        season_param = TODAY.year
        # A lot of functionality depends on future matches for generating predictions
        future = factory.Trait(
            start_date_time=factory.LazyAttributeSequence(_fake_future_datetime)
        )

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        model_instance = model_class(**kwargs)

        if model_instance.winner and model_instance.winner.id is None:
            model_instance.winner.create()

        model_instance.create()
        return model_instance


class TeamMatchFactory(TippingFactory):
    """Factory class for the TeamMatch data model."""

    class Meta:
        """Factory attributes for recreating the associated model's attributes."""

        model = TeamMatch

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

        if model_instance.team.id is None:
            model_instance.team.create()

        if model_instance.match.id is None:
            model_instance.match.create()

        model_instance.create()
        return model_instance
