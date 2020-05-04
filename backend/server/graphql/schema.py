"""GraphQL schema for all queries."""

from typing import List
from functools import partial

import graphene
from django.db.models import QuerySet
from django.utils import timezone
from django.db.models import Count
from mypy_extensions import TypedDict

from server.models import Prediction, Match, MLModel
from server.graphql import cumulative_calculations
from server.types import RoundMetrics
from .types import (
    SeasonType,
    PredictionType,
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


class RoundMetricsType(graphene.ObjectType):
    """Cumulative performance Metrics for Tipresias competition models."""

    season = graphene.NonNull(graphene.Int)
    match__round_number = graphene.NonNull(graphene.Int, name="roundNumber")

    cumulative_correct_count = graphene.Int(
        description=("Cumulative sum of correct tips for the given season"),
        default_value=0,
        required=True,
    )
    cumulative_accuracy = graphene.Float(
        description=(
            "Cumulative mean of correct tips (i.e. accuracy) for the given season."
        ),
        default_value=0,
        required=True,
    )
    cumulative_mean_absolute_error = graphene.Float(
        description="Cumulative mean absolute error for the given season",
        default_value=0,
        required=True,
    )
    cumulative_margin_difference = graphene.Int(
        description=(
            "Cumulative difference between predicted margin and actual margin "
            "for the given season."
        ),
        default_value=0,
        required=True,
    )
    cumulative_bits = graphene.Float(
        description="Cumulative bits metric for the given season.",
        default_value=0,
        required=True,
    )

    @staticmethod
    def resolve_season(root: RoundMetrics, _info):
        """Get season value from match__start_date_time."""
        return root["match__start_date_time"].year


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

    fetch_latest_round_metrics = graphene.Field(
        RoundMetricsType,
        description=(
            "Performance metrics for Tipresias models for the current season "
            "through the last-played round."
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
    def resolve_fetch_latest_round_metrics(_root, _info) -> RoundMetrics:
        """
        Return performance metrics for competition models through the last-played round.
        """
        max_match = (
            Match.objects.filter(start_date_time__lt=timezone.now())
            .order_by("-start_date_time")
            .first()
        )

        prediction_query_set = Prediction.objects.filter(
            match__start_date_time__year=max_match.year,
            ml_model__used_in_competitions=True,
        ).select_related("ml_model", "match")

        metric_values = cumulative_calculations.query_database_for_prediction_metrics(
            prediction_query_set
        ).values(
            *cumulative_calculations.REQUIRED_VALUES_FOR_METRICS,
            "match__id",
            "ml_model__is_principle",
            "ml_model__used_in_competitions",
        )

        consolidated_metrics = (
            cumulative_calculations.calculate_cumulative_metrics(metric_values)
            .pipe(
                partial(
                    cumulative_calculations.filter_by_round,
                    round_number=max_match.round_number,
                )
            )
            .pipe(cumulative_calculations.consolidate_competition_predictions)
            .to_dict("records")
        )

        assert len(consolidated_metrics) == 1, (
            "Latest round predictions should be in the form of a single data set "
            "composed of all competition models, but multiple sets were calculated:\n"
            f"{consolidated_metrics}"
        )

        return consolidated_metrics[0]

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
