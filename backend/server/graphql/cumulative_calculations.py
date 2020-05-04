"""Functions for calculating model prediction metrics."""

from typing import List, Optional

from django.db.models import (
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
from django.utils import timezone
import pandas as pd
import numpy as np

from server.models import TeamMatch
from server.types import MetricValues


# For regressors that might try to predict negative values or 0,
# we need a slightly positive minimum to not get errors when calculating logarithms
MIN_LOG_VAL = 1 * 10 ** -10

GROUP_BY_LVL = 0
ROUND_NUMBER_LVL = 0

REQUIRED_VALUES_FOR_METRICS = [
    "match__start_date_time",
    "match__round_number",
    "ml_model__name",
    "predicted_margin",
    "predicted_win_probability",
    "predicted_winner__name",
    "match__winner__name",
    "match__margin",
    "absolute_margin_diff",
    "cumulative_correct_count",
    "cumulative_accuracy",
]


def consolidate_competition_predictions(data_frame: pd.DataFrame,) -> pd.DataFrame:
    """
    Join prediction data for all competition models for official Tipresias data.

    Consolidates the disparate prediction types and uses the principle model
    for predicting winners.

    Params:
    -------
    data_frame: ML model prediction or metric data.
    """
    assert data_frame["ml_model__used_in_competitions"].all()

    principle_data = (
        data_frame.query("ml_model__is_principle == True")
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
        data_frame.query("ml_model__is_principle == False")
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

    return principle_data.fillna(non_principle_data)


def filter_by_round(data_frame: pd.DataFrame, round_number: Optional[int] = None):
    """
    Filter metric data by round number.

    Params:
    -------
    data_frame: The data frame to be filtered.
    round_number: Only includes data from this round. '-1' filters
        for last round available. 'None' returns all rounds.
    """
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
        data_frame["absolute_margin_diff"] == 0,
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


def calculate_cumulative_metrics(metric_values: List[MetricValues]) -> pd.DataFrame:
    """Calculate cumulative metrics that can't be calculated in SQL."""
    return (
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


def query_database_for_prediction_metrics(prediction_query_set: QuerySet,) -> QuerySet:
    """Query the database for data needed to calculate cumulative metrics."""
    return (
        prediction_query_set.order_by("match__start_date_time")
        # We don't want to include unplayed matches, which would impact
        # mean-based metrics like accuracy and MAE
        .filter(match__start_date_time__lt=timezone.localtime()).annotate(
            tip_point=_calculate_tip_points(),
            match__winner__name=_get_match_winner_name(),
            match__margin=(
                Max("match__teammatch__score") - Min("match__teammatch__score")
            ),
            absolute_margin_diff=_calculate_absolute_margin_difference(),
            cumulative_correct_count=_calculate_cumulative_correct(),
            cumulative_accuracy=_calculate_cumulative_accuracy(),
        )
    )
