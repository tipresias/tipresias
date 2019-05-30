# Due to GraphQL magic, all the resolver methods require `self`, but don't actually
# use it, so we need to silence the suggestions to make everything a staticmethod
# pylint: disable=R0201

from datetime import date

import graphene
from graphene_django.types import DjangoObjectType
from django.db.models import Count, Q
import pandas as pd

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
    """Basic prediction type based on Prediction data model"""

    class Meta:
        model = Prediction


class ModelPredictionType(graphene.ObjectType):
    """
    Stats for predictions made by the given model through the given round
    """

    model_name = graphene.String()
    cumulative_correct_count = graphene.Int()

    def resolve_model_name(self, _info):
        return self.get("model_name")

    def resolve_cumulative_correct_count(self, _info):
        return self.get("cumulative_correct_count")


class RoundPredictionType(graphene.ObjectType):
    """Predictions for the year grouped by round"""

    round_number = graphene.Int()
    model_predictions = graphene.List(
        ModelPredictionType,
        description=(
            "Stats for predictions made by the given model through the given round"
        ),
    )

    def resolve_round_number(self, _info):
        return self.get("match__round_number")

    def resolve_model_predictions(self, _info):
        return [
            {"model_name": model_name, "cumulative_correct_count": correct_count}
            for model_name, correct_count in self.items()
            if model_name != "match__round_number"
        ]


class YearlyPredictionsType(graphene.ObjectType):
    """Model prediction stats per year"""

    prediction_model_names = graphene.List(
        graphene.String, description="All model names available for the given year"
    )
    predictions_by_round = graphene.List(
        RoundPredictionType, description=("Predictions for the year grouped by round")
    )

    def resolve_prediction_model_names(self, _info):
        return self.distinct("ml_model__name").values_list("ml_model__name", flat=True)

    def resolve_predictions_by_round(self, _info):
        query_set = (
            self.values("match__round_number", "ml_model__name")
            .order_by("match__round_number")
            .annotate(correct_count=Count("is_correct", filter=Q(is_correct=True)))
        )

        calculate_cumulative_correct = (
            lambda df: df.groupby("ml_model__name")
            .expanding()
            .sum()
            .reset_index(level=0)["correct_count"]
            .rename("cumulative_correct_count")
        )

        # TODO: There's definitely a way to do these calculations via SQL, but chained
        # GROUP BYs and calculations based on calculations is a bit much for me
        # right now, so I'll come back and figure it out later
        return (
            pd.DataFrame(list(query_set))
            .assign(cumulative_correct=calculate_cumulative_correct)
            .pivot(
                columns="ml_model__name",
                values="cumulative_correct",
                index="match__round_number",
            )
            .reset_index()
            .fillna(0)
            .to_dict("records")
        )


class Query(graphene.ObjectType):
    predictions = graphene.List(
        PredictionType,
        year=graphene.Int(default_value=None),
        description="Basic prediction type based on Prediction data model",
    )

    prediction_years = graphene.List(
        graphene.Int,
        description="All years for which model predictions exist in the database",
    )

    yearly_predictions = graphene.Field(
        YearlyPredictionsType,
        year=graphene.Int(),
        description="Model prediction stats per year",
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

    def resolve_yearly_predictions(self, _info, year=date.today().year):
        return Prediction.objects.filter(
            match__start_date_time__year=year
        ).select_related("ml_model", "match")


schema = graphene.Schema(query=Query)
