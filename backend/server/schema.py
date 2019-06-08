from typing import List, cast
from datetime import date

import graphene
from graphene_django.types import DjangoObjectType
from django.db.models import Count, Q, QuerySet, Max
import pandas as pd
from mypy_extensions import TypedDict

from server.models import Prediction, MLModel, TeamMatch, Match, Team


ModelPrediction = TypedDict(
    "ModelPrediction", {"ml_model__name": str, "cumulative_correct_count": int}
)

RoundPrediction = TypedDict(
    "RoundPrediction",
    {
        "match__round_number": int,
        "model_predictions": List[ModelPrediction],
        "matches": QuerySet,
    },
)

TIPRESIAS = "tipresias"


class TeamType(DjangoObjectType):
    class Meta:
        model = Team


class MatchType(DjangoObjectType):
    class Meta:
        model = Match

    winner = graphene.Field(TeamType)
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


class CumulativePredictionsByRoundType(graphene.ObjectType):
    """
    Cumulative stats for predictions made by the given model through the given round
    """

    ml_model__name = graphene.String(name="modelName")
    cumulative_correct_count = graphene.Int(
        description=(
            "Cumulative sum of correct tips made by the given model "
            "for the given season"
        ),
        default_value=0,
    )


class RoundType(graphene.ObjectType):
    """Match and prediction data for a given season grouped by round"""

    match__round_number = graphene.Int(name="roundNumber")
    model_predictions = graphene.List(
        CumulativePredictionsByRoundType,
        description=(
            "Cumulative stats for predictions made by the given model "
            "through the given round"
        ),
        default_value=pd.DataFrame(),
    )
    matches = graphene.List(MatchType, default_value=[])

    @staticmethod
    def resolve_model_predictions(root, _info) -> List[ModelPrediction]:
        model_predictions_to_dict = lambda df: [
            {df.index.names[0]: value, **df.loc[value, :].to_dict()}
            for value in df.index
        ]

        prediction_dicts = root.get("model_predictions").pipe(model_predictions_to_dict)

        return [
            cast(ModelPrediction, model_prediction)
            for model_prediction in prediction_dicts
        ]


class SeasonType(graphene.ObjectType):
    """Match and prediction data grouped by season"""

    prediction_model_names = graphene.List(
        graphene.String, description="All model names available for the given year"
    )
    predictions_by_round = graphene.List(
        RoundType, description="Match and prediction data grouped by round"
    )

    @staticmethod
    def resolve_prediction_model_names(root, _info) -> List[str]:
        return root.distinct("ml_model__name").values_list("ml_model__name", flat=True)

    @staticmethod
    def resolve_predictions_by_round(root, _info) -> List[RoundPrediction]:
        query_set = (
            root.values("match__round_number", "ml_model__name")
            .order_by("match__round_number")
            .annotate(correct_count=Count("is_correct", filter=Q(is_correct=True)))
        )

        # TODO: There's definitely a way to do these calculations via SQL, but chained
        # GROUP BYs and calculations based on calculations is a bit much for me
        # right now, so I'll come back and figure it out later
        calculate_cumulative_correct = (
            lambda df: df.groupby("ml_model__name")
            .expanding()
            .sum()
            .reset_index(level=0)["correct_count"]
            .rename("cumulative_correct_count")
        )

        round_predictions = lambda df: [
            {
                df.index.names[0]: value,
                "model_predictions": df.xs(value, level=0),
                "matches": Match.objects.filter(
                    id__in=query_set.filter(match__round_number=value).values_list(
                        "match", flat=True
                    )
                ),
            }
            for value in df.index.levels[0]
        ]

        return (
            pd.DataFrame(list(query_set))
            .assign(cumulative_correct=calculate_cumulative_correct)
            .groupby(["match__round_number", "ml_model__name"])
            .mean()
            .pipe(round_predictions)
        )


class Query(graphene.ObjectType):
    predictions = graphene.List(PredictionType, year=graphene.Int(default_value=None))

    prediction_years = graphene.List(
        graphene.Int,
        description="All years for which model predictions exist in the database",
    )

    yearly_predictions = graphene.Field(
        SeasonType, year=graphene.Int(default_value=date.today().year)
    )

    latest_round_predictions = graphene.Field(
        RoundType,
        ml_model_name=graphene.String(default_value=TIPRESIAS),
        description=(
            "Match info and predictions for the latest round for which data "
            "is available"
        ),
    )

    @staticmethod
    def resolve_predictions(_root, _info, year=None) -> QuerySet:
        if year is None:
            return Prediction.objects.all()

        return Prediction.objects.filter(match__start_date_time__year=year)

    @staticmethod
    def resolve_prediction_years(_root, _info) -> List[int]:
        return (
            Prediction.objects.select_related("match")
            .distinct("match__start_date_time__year")
            .order_by("match__start_date_time__year")
            .values_list("match__start_date_time__year", flat=True)
        )

    @staticmethod
    def resolve_yearly_predictions(_root, _info, year) -> QuerySet:
        return Prediction.objects.filter(
            match__start_date_time__year=year
        ).select_related("ml_model", "match")

    @staticmethod
    def resolve_latest_round_predictions(
        _root, _info, ml_model_name
    ) -> RoundPrediction:
        current_season = date.today().year
        current_season_matches = Match.objects.filter(
            start_date_time__year=current_season
        )
        max_round_number = (
            current_season_matches.aggregate(Max("round_number")).get(
                "round_number__max"
            )
            or 0
        )

        matches = (
            current_season_matches.filter(
                round_number=max_round_number, prediction__ml_model__name=ml_model_name
            )
            .prefetch_related("prediction_set", "teammatch_set")
            .order_by("start_date_time")
        )

        return {
            "match__round_number": max_round_number,
            "model_predictions": pd.DataFrame(),
            "matches": matches,
        }


schema = graphene.Schema(query=Query)
