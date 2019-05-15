from datetime import date, datetime

import factory
from factory.django import DjangoModelFactory
import numpy as np
from faker import Faker

from server.models import Team, Prediction, Match, MLModel, TeamMatch
from machine_learning.data_config import TEAM_NAMES, VENUES
from machine_learning.tests.fixtures import TestEstimator
from project.settings.common import MELBOURNE_TIMEZONE

FAKE = Faker()
THIS_YEAR = date.today().year
JAN = 1
FIRST = 1
DEC = 12
THIRTY_FIRST = 31


class TeamFactory(DjangoModelFactory):
    class Meta:
        model = Team
        django_get_or_create = ("name",)

    name = factory.Sequence(lambda n: TEAM_NAMES[n % len(TEAM_NAMES)])


class MatchFactory(DjangoModelFactory):
    class Meta:
        model = Match

    class Params:
        year = THIS_YEAR

    start_date_time = factory.LazyAttribute(
        lambda obj: FAKE.date_time_between_dates(
            datetime_start=datetime(obj.year, JAN, FIRST),
            datetime_end=datetime(obj.year, DEC, THIRTY_FIRST),
            tzinfo=MELBOURNE_TIMEZONE,
        )
    )
    round_number = np.random.randint(1, 24)
    venue = VENUES[np.random.randint(0, len(VENUES) - 1)]


class TeamMatchFactory(DjangoModelFactory):
    class Meta:
        model = TeamMatch

    team = factory.SubFactory(TeamFactory)
    match = factory.SubFactory(MatchFactory)
    at_home = factory.Faker("pybool")
    score = np.random.randint(50, 150)


class MLModelFactory(DjangoModelFactory):
    class Meta:
        model = MLModel

    name = factory.Faker("company")
    description = factory.Faker("paragraph", nb_sentences=4)
    filepath = TestEstimator().pickle_filepath()
    data_class_path = ""


class PredictionFactory(DjangoModelFactory):
    class Meta:
        model = Prediction

    match = factory.SubFactory(MatchFactory)
    ml_model = factory.SubFactory(MLModelFactory)
    predicted_winner = factory.SubFactory(TeamFactory)
    predicted_margin = np.random.randint(0, 50)


class FullMatchFactory(MatchFactory):
    prediction = factory.RelatedFactory(PredictionFactory, "match")
    home_team_match = factory.RelatedFactory(TeamMatchFactory, "match", at_home=True)
    away_team_match = factory.RelatedFactory(TeamMatchFactory, "match", at_home=False)
