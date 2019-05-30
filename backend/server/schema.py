# Due to GraphQL magic, all the resolver methods require `self`, but don't actually
# use it, so we need to silence the suggestions to make everything a staticmethod
# pylint: disable=R0201

from datetime import date

import graphene
from graphene_django.types import DjangoObjectType

from server.models import Prediction, MLModel, TeamMatch, Match, Team


class TeamType(DjangoObjectType):
    class Meta:
        model = Team


class MatchType(DjangoObjectType):
    class Meta:
        model = Match

    winner = graphene.Field(TeamType, id=graphene.Int(), name=graphene.String())
    year = graphene.Int()


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


class CorrectPredictionCount(graphene.ObjectType):
    """Cumulative correct predictions for the year broken down by round"""

    model_name = graphene.String()
    round_number = graphene.Int()
    is_correct = graphene.Boolean()

    def resolve_model_name(self, _info):
        return self.ml_model.name

    def resolve_round_number(self, _info):
        return self.match.round_number


class CumulativePredictionsType(graphene.ObjectType):
    """Cumulative model prediction stats per year"""

    prediction_model_names = graphene.List(graphene.String)
    cumulative_correct_predictions = graphene.List(
        CorrectPredictionCount,
        description="Cumulative correct predictions for the year broken down by round",
    )

    def resolve_prediction_model_names(self, _info):
        return self.distinct("ml_model__name").values_list("ml_model__name", flat=True)

    def resolve_cumulative_correct_predictions(self, _info):
        return self


class Query(graphene.ObjectType):
    predictions = graphene.List(PredictionType, year=graphene.Int(default_value=None))

    prediction_years = graphene.List(
        graphene.Int,
        description="All years for which model predictions exist in the database",
    )

    cumulative_predictions = graphene.Field(
        CumulativePredictionsType,
        year=graphene.Int(),
        description="Cumulative model prediction stats per year",
    )

    def resolve_predictions(self, _info, year=None):
        if year is None:
            return Prediction.objects.all()

        return Prediction.objects.filter(match__start_date_time__year=year)

    def resolve_prediction_years(self, _info):
        return (
            Prediction.objects.select_related("match")
            .distinct("match__start_date_time__year")
            .order_by("match__start_date_time__year")
            .values_list("match__start_date_time__year", flat=True)
        )

    def resolve_cumulative_predictions(self, _info, year=date.today().year):
        return Prediction.objects.filter(
            match__start_date_time__year=year
        ).select_related("ml_model", "match")


schema = graphene.Schema(query=Query)
