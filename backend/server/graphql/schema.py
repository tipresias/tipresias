"""GraphQL schema for all queries."""

from typing import List

import graphene
from django.utils import timezone
from django.db.models import QuerySet, Count
from mypy_extensions import TypedDict
import pandas as pd
import numpy as np

from server.models import Prediction, Match, MLModel
from server.types import RoundMetrics
from server.graphql.calculations import calculate_cumulative_metrics
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

RoundModelMetrics = TypedDict(
    "RoundModelMetrics",
    {"match__round_number": int, "model_metrics": pd.DataFrame, "matches": QuerySet},
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
    cumulative_margin_difference = graphene.Float(
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
    def resolve_season(round_metrics: RoundMetrics, _info):
        """Get season value from match__start_date_time."""
        return round_metrics["match__start_date_time"].year


def _consolidate_competition_model_metrics(model_metrics: pd.DataFrame) -> RoundMetrics:
    assert model_metrics["ml_model__used_in_competitions"].all()

    principal_data = (
        model_metrics.query("ml_model__is_principal == True")
        .reset_index(drop=False)
        .set_index("match__id")
        # We replace previously-filled values with NaNs to make it easier to fill
        # missing principal metrics with metrics from the other competition models.
        # It's okay if we NaNify a legitimate 0/0.5, because the other model(s)
        # will just fill the NaN with the same neutral value.
        .replace(
            to_replace={
                "cumulative_mean_absolute_error": 0,
                "cumulative_margin_difference": 0,
                "cumulative_bits": 0,
                "predicted_margin": 0,
                "predicted_win_probability": 0.5,
            },
            value={
                "cumulative_mean_absolute_error": np.nan,
                "cumulative_margin_difference": np.nan,
                "cumulative_bits": np.nan,
                "predicted_margin": np.nan,
                "predicted_win_probability": np.nan,
            },
        )
    )

    non_principal_data = (
        model_metrics.query("ml_model__is_principal == False")
        .fillna(0)
        .replace(
            to_replace={"predicted_win_probability": 0.5},
            value={"predicted_win_probability": 0},
        )
        .select_dtypes("number")
        .groupby("match__id")
        # We can sum because each prediction type will only have one model with values,
        # and the rest of the rows will be zeros.
        .sum()
    )

    consolidated_metrics = principal_data.fillna(non_principal_data).to_dict("records")

    assert len(consolidated_metrics) == 1, (
        "Latest round predictions should be in the form of a single data set "
        "composed of all competition models, but multiple sets were calculated:\n"
        f"{consolidated_metrics}"
    )

    return consolidated_metrics[0]


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
                sorted(
                    Prediction.objects.select_related("match")
                    # If we don't have any match/prediction results yet, there won't be
                    # any performance metrics to calculate
                    .filter(is_correct__isnull=False)
                    .distinct("match__start_date_time__year")
                    .values_list("match__start_date_time__year", flat=True)
                )
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
        matches_with_predictions = Match.objects.annotate(
            prediction_count=Count("prediction")
        ).filter(prediction_count__gt=0)
        max_match_with_predictions = max(
            matches_with_predictions, key=lambda match: match.start_date_time
        )

        prediction_query = Prediction.objects.filter(
            match__start_date_time__year=max_match_with_predictions.start_date_time.year,
            match__round_number=max_match_with_predictions.round_number,
            ml_model__used_in_competitions=True,
        )

        return {
            "round_number": max_match_with_predictions.round_number,
            "match_predictions": prediction_query,
        }

    @staticmethod
    def resolve_fetch_latest_round_metrics(_root, _info) -> RoundMetrics:
        """
        Return performance metrics for competition models through the last-played round.
        """
        matches_with_results = Match.objects.filter(
            start_date_time__lt=timezone.now(), teammatch__score__gt=0
        )
        max_match_with_results = max(
            matches_with_results, key=lambda match: match.start_date_time
        )

        metric_values = (
            Prediction.objects.filter(
                match__start_date_time__year=max_match_with_results.year,
                ml_model__used_in_competitions=True,
                # We don't want to include matches without results, which would impact
                # mean-based metrics like accuracy and MAE
                match__teammatch__score__gt=0,
            )
            .select_related("ml_model", "match")
            .values(
                "match__id",
                "match__margin",
                "match__winner__name",
                "match__round_number",
                "match__start_date_time",
                "ml_model__is_principal",
                "ml_model__name",
                "ml_model__used_in_competitions",
                "predicted_margin",
                "predicted_winner__name",
                "predicted_win_probability",
                "is_correct",
            )
        )

        metrics_df = calculate_cumulative_metrics(
            metric_values, max_match_with_results.round_number
        )

        return _consolidate_competition_model_metrics(metrics_df)

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
