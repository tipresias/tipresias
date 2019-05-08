import factory
from factory.django import DjangoModelFactory
import numpy as np

from server.models import Team, Prediction, Match, MLModel, TeamMatch
from server.types import FixtureData
from machine_learning.data_config import TEAM_NAMES, VENUE_CITIES
from machine_learning.tests.fixtures import TestEstimator
from project.settings.common import MELBOURNE_TIMEZONE

VENUES = list(VENUE_CITIES.keys())


class TeamFactory(DjangoModelFactory):
    class Meta:
        model = Team
        django_get_or_create = ("name",)

    name = factory.Sequence(lambda n: TEAM_NAMES[n % len(TEAM_NAMES)])


class MatchFactory(DjangoModelFactory):
    class Meta:
        model = Match

    start_date_time = factory.Faker("date_this_year", tzinfo=MELBOURNE_TIMEZONE)
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
