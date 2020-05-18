"""GraphQL schema for all queries."""

from typing import List, Optional
from functools import partial

import graphene
from django.utils import timezone
from django.db.models import (
    Count,
    Case,
    When,
    Value,
    IntegerField,
    Subquery,
    OuterRef,
    Max,
    Min,
    Func,
    F,
    Sum,
    Window,
    Avg,
    QuerySet,
)
from mypy_extensions import TypedDict
import pandas as pd
import numpy as np

from server.models import Prediction, Match, MLModel, TeamMatch
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

RoundModelMetrics = TypedDict(
    "RoundModelMetrics",
    {"match__round_number": int, "model_metrics": pd.DataFrame, "matches": QuerySet},
)


ROUND_NUMBER_LVL = 0
GROUP_BY_LVL = 0
# For regressors that might try to predict negative values or 0,
# we need a slightly positive minimum to not get errors when calculating logarithms
MIN_LOG_VAL = 1 * 10 ** -10


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


def _filter_by_round(data_frame: pd.DataFrame, round_number: Optional[int] = None):
    if round_number is None:
        return data_frame

    round_number_filter = (
        data_frame.index.get_level_values(ROUND_NUMBER_LVL).max()
        if round_number == -1
        else round_number
    )

    return data_frame.loc[(round_number_filter, slice(None)), :]


def _calculate_cumulative_bits(data_frame: pd.DataFrame):
    return (
        data_frame.groupby("ml_model__name")
        .expanding()["bits"]
        .sum()
        .rename("cumulative_bits")
        .reset_index(level=GROUP_BY_LVL, drop=True)
    )


# Raw bits calculations per http://probabilistic-footy.monash.edu/~footy/about.shtml
def _calculate_bits(data_frame: pd.DataFrame):
    positive_pred = lambda y_pred: (
        np.maximum(y_pred, np.repeat(MIN_LOG_VAL, len(y_pred)))
    )
    draw_bits = lambda y_pred: (
        1 + (0.5 * np.log2(positive_pred(y_pred * (1 - y_pred))))
    )
    win_bits = lambda y_pred: 1 + np.log2(positive_pred(y_pred))
    loss_bits = lambda y_pred: 1 + np.log2(positive_pred(1 - y_pred))

    return np.where(
        data_frame["match__margin"] == 0,
        draw_bits(data_frame["predicted_win_probability"]),
        np.where(
            data_frame["match__winner__name"] == data_frame["predicted_winner__name"],
            win_bits(data_frame["predicted_win_probability"]),
            loss_bits(data_frame["predicted_win_probability"]),
        ),
    )


# TODO: I've migrated the simple calculations over to SQL, but calculations
# based on margin_diff are difficult, because Django doesn't allow an annotation
# based on an aggregation (margin_diff uses Max/Min), and `Window` can't be used
# in an `aggregate` call. I may need to resort to raw SQL, but that would probably
# still require figuring out why the ORM doesn't like this combination.
def _calculate_cumulative_mae(data_frame: pd.DataFrame):
    return (
        data_frame.groupby("ml_model__name")
        .expanding()["absolute_margin_diff"]
        .mean()
        .round(2)
        .rename("cumulative_mean_absolute_error")
        .reset_index(level=GROUP_BY_LVL, drop=True)
    )


def _calculate_cumulative_margin_difference(data_frame: pd.DataFrame):
    return (
        data_frame.groupby("ml_model__name")
        .expanding()["absolute_margin_diff"]
        .sum()
        .rename("cumulative_margin_difference")
        .reset_index(level=GROUP_BY_LVL, drop=True)
    )


def _calculate_cumulative_accuracy():
    return Window(
        expression=Avg("tip_point"),
        partition_by=F("ml_model_id"),
        order_by=F("match__start_date_time").asc(),
    )


def _calculate_cumulative_correct():
    return Window(
        expression=Sum("tip_point"),
        partition_by=F("ml_model_id"),
        order_by=F("match__start_date_time").asc(),
    )


def _calculate_absolute_margin_difference():
    return Case(
        When(
            is_correct=True,
            then=Func(F("predicted_margin") - F("match__margin"), function="ABS"),
        ),
        default=(F("predicted_margin") + F("match__margin")),
        output_field=IntegerField(),
    )


def _get_match_winner_name():
    return Subquery(
        TeamMatch.objects.filter(match_id=OuterRef("match_id"))
        .order_by("-score")
        .values_list("team__name")[:1]
    )


def _calculate_tip_points():
    return Case(
        When(is_correct=True, then=Value(1)),
        default=Value(0),
        output_field=IntegerField(),
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

        metric_values = (
            Prediction.objects.filter(
                match__start_date_time__year=max_match.year,
                ml_model__used_in_competitions=True,
                # We don't want to include unplayed matches, which would impact
                # mean-based metrics like accuracy and MAE
                match__start_date_time__lt=timezone.localtime(),
            )
            .select_related("ml_model", "match")
            .order_by("match__start_date_time")
            .annotate(
                tip_point=_calculate_tip_points(),
                match__winner__name=_get_match_winner_name(),
                match__margin=(
                    Max("match__teammatch__score") - Min("match__teammatch__score")
                ),
                absolute_margin_diff=_calculate_absolute_margin_difference(),
                cumulative_correct_count=_calculate_cumulative_correct(),
                cumulative_accuracy=_calculate_cumulative_accuracy(),
            )
            .values(
                "match__start_date_time",
                "match__start_date_time__year",
                "match__round_number",
                "ml_model__name",
                "ml_model__used_in_competitions",
                "predicted_margin",
                "predicted_win_probability",
                "predicted_winner__name",
                "match__winner__name",
                "match__margin",
                "absolute_margin_diff",
                "cumulative_correct_count",
                "cumulative_accuracy",
                "match__id",
                "ml_model__is_principle",
            )
        )

        metrics_df = (
            pd.DataFrame(metric_values)
            # We fill missing win probabilities with 0.5, because that's the equivalent
            # of not picking a winner. 0 would represent an extreme prediction
            # and result in large negative bits calculations.
            .fillna({"predicted_win_probability": 0.5})
            .fillna(0)
            .assign(bits=_calculate_bits)
            .assign(
                cumulative_margin_difference=_calculate_cumulative_margin_difference,
                cumulative_bits=_calculate_cumulative_bits,
                cumulative_mean_absolute_error=_calculate_cumulative_mae,
            )
            .groupby(["match__round_number", "ml_model__name"])
            .last()
            .pipe(partial(_filter_by_round, round_number=max_match.round_number))
        )

        assert metrics_df["ml_model__used_in_competitions"].all()

        principle_data = (
            metrics_df.query("ml_model__is_principle == True")
            .reset_index(drop=False)
            .set_index("match__id")
            # We replace previously-filled values with NaNs to make it easier to fill
            # missing principle metrics with metrics from the other competition models.
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

        non_principle_data = (
            metrics_df.query("ml_model__is_principle == False")
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

        consolidated_metrics = principle_data.fillna(non_principle_data).to_dict(
            "records"
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
