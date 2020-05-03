"""GraphQL schema for all queries."""

from typing import List

import graphene
from django.db.models import QuerySet
from django.utils import timezone
from django.db.models import Count
import pandas as pd
from mypy_extensions import TypedDict

from server.models import Prediction, Match, MLModel
from server.graphql.types.season import RoundModelMetrics
from .types import (
    SeasonType,
    PredictionType,
    RoundType,
    MLModelType,
    SeasonPerformanceChartParametersType,
    RoundPredictionType,
)


SeasonPerformanceChartParameters = TypedDict(
    "SeasonPerformanceChartParameters",
    {"available_seasons": List[int], "available_ml_models": List[MLModel]},
)

RoundPredictions = TypedDict(
    "RoundPredictions", {"round_number": int, "match_predictions": QuerySet}
)


class Query(graphene.ObjectType):
    """Base GraphQL Query type that contains all queries and their resolvers."""

    fetch_predictions = graphene.List(
        graphene.NonNull(PredictionType), year=graphene.Int(), required=True
    )

    fetch_season_performance_chart_parameters = graphene.Field(
        SeasonPerformanceChartParametersType,
        description=(
            "Parameters for displaying info and populating inputs "
            "for the season performance chart."
        ),
        required=True,
    )

    fetch_season_years = graphene.List(
        graphene.NonNull(graphene.Int),
        description="All years for which model predictions exist in the database",
        required=True,
    )

    fetch_season_model_metrics = graphene.Field(
        SeasonType,
        season=graphene.Int(
            default_value=timezone.localtime().year,
            description=("Filter metrics by season."),
        ),
        required=True,
    )

    fetch_latest_round_predictions = graphene.Field(
        RoundPredictionType,
        description=(
            "Official Tipresias predictions for the latest round for which data "
            "is available"
        ),
        required=True,
    )

    fetch_ml_models = graphene.List(
        graphene.NonNull(MLModelType),
        for_competition_only=graphene.Boolean(
            default_value=False,
            description=(
                "competition_only: Whether to filter ML models such that only "
                "the models whose predictions are submitted to competitions "
                "are returned. There are no more than one model per type of prediction "
                "(e.g. margin, win probability)."
            ),
        ),
        required=True,
    )

    @staticmethod
    def resolve_fetch_predictions(_root, _info, year=None) -> QuerySet:
        """Return all predictions from the given year or from all years."""
        if year is None:
            return Prediction.objects.all()

        return Prediction.objects.filter(match__start_date_time__year=year)

    @staticmethod
    def resolve_fetch_season_performance_chart_parameters(
        _root, _info
    ) -> SeasonPerformanceChartParameters:
        """
        Return parameters for labels and inputs for the performance chart.
        """
        return {
            "available_seasons": (
                Prediction.objects.select_related("match")
                .distinct("match__start_date_time__year")
                .order_by("match__start_date_time__year")
                .values_list("match__start_date_time__year", flat=True)
            ),
            "available_ml_models": (
                MLModel.objects.prefetch_related("prediction_set")
                .annotate(prediction_count=Count("prediction"))
                .filter(prediction_count__gt=0)
            ),
        }

    @staticmethod
    def resolve_fetch_season_model_metrics(_root, _info, season) -> QuerySet:
        """Return all model performance metrics from the given season."""
        return Prediction.objects.filter(
            match__start_date_time__year=season
        ).select_related("ml_model", "match")

    @staticmethod
    def resolve_fetch_latest_round_predictions(_root, _info) -> RoundPredictions:
        """Return predictions and model metrics for the latest available round."""
        max_match = Match.objects.order_by("-start_date_time").first()

        prediction_query = Prediction.objects.filter(
            match__start_date_time__year=max_match.start_date_time.year,
            match__round_number=max_match.round_number,
            ml_model__used_in_competitions=True,
        ).order_by("match__start_date_time")

        return {
            "round_number": max_match.round_number,
            "match_predictions": prediction_query,
        }

    @staticmethod
    def resolve_fetch_ml_models(
        _root, _info, for_competition_only: bool
    ) -> List[MLModel]:
        """
        Return machine-learning models.

        Params:
        -------
        for_competition_only: Whether to filter ML models such that only the models
            whose predictions are submitted to competitions are returned.
        """

        ml_models = MLModel.objects

        if for_competition_only:
            return ml_models.filter(used_in_competitions=True)

        return ml_models.all()
