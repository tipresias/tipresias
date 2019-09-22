from datetime import date, datetime
import pytz

import factory
from factory.django import DjangoModelFactory
from faker import Faker
from django.utils import timezone
from django.conf import settings

from server.models import Team, Prediction, Match, MLModel, TeamMatch

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

    name = factory.Sequence(lambda n: settings.TEAM_NAMES[n % len(settings.TEAM_NAMES)])


class MatchFactory(DjangoModelFactory):
    class Meta:
        model = Match

    class Params:
        year = THIS_YEAR

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


class TeamMatchFactory(DjangoModelFactory):
    class Meta:
        model = TeamMatch

    team = factory.SubFactory(TeamFactory)
    match = factory.SubFactory(MatchFactory)
    at_home = factory.Faker("pybool")
    score = factory.Faker("pyint", min_value=50, max_value=150)


class MLModelFactory(DjangoModelFactory):
    class Meta:
        model = MLModel

    name = factory.Faker("company")
    description = factory.Faker("paragraph", nb_sentences=4)
    filepath = "some/filepath/to/model.pkl"
    data_class_path = ""


class PredictionFactory(DjangoModelFactory):
    class Meta:
        model = Prediction

    match = factory.SubFactory(MatchFactory)
    ml_model = factory.SubFactory(MLModelFactory)
    predicted_winner = factory.SubFactory(TeamFactory)
    predicted_margin = factory.Faker("pyint", min_value=0, max_value=50)
    is_correct = factory.Faker("pybool")


class FullMatchFactory(MatchFactory):
    prediction = factory.RelatedFactory(PredictionFactory, "match")
    prediction_two = factory.RelatedFactory(PredictionFactory, "match")

    home_team_match = factory.RelatedFactory(TeamMatchFactory, "match", at_home=True)
    away_team_match = factory.RelatedFactory(TeamMatchFactory, "match", at_home=False)
