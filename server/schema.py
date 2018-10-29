import os
import graphene
from graphene_django.types import DjangoObjectType

from server.models import Prediction, MLModel, TeamMatch, Match, Team

PROJECT_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '../')
)


class TeamType(DjangoObjectType):
    class Meta:
        model = Team


class MatchType(DjangoObjectType):
    class Meta:
        model = Match

    winner = TeamType


class TeamMatchType(DjangoObjectType):
    class Meta:
        model = TeamMatch


class MLModelType(DjangoObjectType):
    class Meta:
        model = MLModel


class PredictionType(DjangoObjectType):
    class Meta:
        model = Prediction

    is_correct = graphene.Boolean()


class Query(graphene.ObjectType):
    hello = graphene.String(name=graphene.String(default_value="stranger"))

    predictions = graphene.List(
        PredictionType, year=graphene.Int(default_value=None)
    )

    def resolve_hello(self, _info, name):
        return 'Hello ' + name

    def resolve_predictions(self, args, _context, _info):
        year = args.get('year')

        if year is None:
            return Prediction.objects.all()

        return Prediction.objects.filter(match__start_date_time__year=year)


schema = graphene.Schema(query=Query)
