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
    class Meta:
        model = Team
        django_get_or_create = ("name",)

    name = factory.Sequence(lambda n: settings.TEAM_NAMES[n % len(settings.TEAM_NAMES)])


class MatchFactory(DjangoModelFactory):
    class Meta:
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
        year = TODAY.year
        # A lot of functionality depends on future matches for generating predictions
        future = factory.Trait(
            start_date_time=factory.LazyAttribute(
                lambda obj: FAKE.date_time_between_dates(
                    datetime_start=timezone.make_aware(
                        datetime(obj.year, TODAY.month, TODAY.day + 1)
                    ),
                    datetime_end=timezone.make_aware(
                        datetime(obj.year, DEC, THIRTY_FIRST)
                    ),
                    tzinfo=pytz.UTC,
                )
            )
        )


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
    prediction = factory.RelatedFactory(PredictionFactory, "match")
    prediction_two = factory.RelatedFactory(PredictionFactory, "match")

    home_team_match = factory.RelatedFactory(TeamMatchFactory, "match", at_home=True)
    away_team_match = factory.RelatedFactory(TeamMatchFactory, "match", at_home=False)
