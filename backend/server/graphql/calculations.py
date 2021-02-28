"""Module for shared logic for calculating model metrics."""

from typing import Optional, List, Dict, Any
from functools import partial

import pandas as pd
import numpy as np


CUMULATIVE_METRICS_VALUES = [
    "absolute_margin_diff",
    "cumulative_accuracy",
    "cumulative_correct_count",
    "match__margin",
    "match__round_number",
    "match__start_date_time",
    "match__winner__name",
    "ml_model__name",
    "ml_model__used_in_competitions",
    "predicted_margin",
    "predicted_winner__name",
    "predicted_win_probability",
]
ROUND_NUMBER_LVL = 0
GROUP_BY_LVL = 0
# For regressors that might try to predict negative values or 0,
# we need a slightly positive minimum to not get errors when calculating logarithms
MIN_LOG_VAL = 1 * 10 ** -10


def _calculate_cumulative_accuracy(data_frame):
    return (
        data_frame.groupby("ml_model__name")
        .expanding()["tip_point"]
        .mean()
        .reset_index(level=GROUP_BY_LVL, drop=True)
    )


def _calculate_cumulative_correct(data_frame):
    return (
        data_frame.groupby("ml_model__name")
        .expanding()["tip_point"]
        .sum()
        .reset_index(level=GROUP_BY_LVL, drop=True)
    )


def _calculate_absolute_margin_difference(data_frame):
    return np.where(
        data_frame["is_correct"],
        (data_frame["match__margin"] - data_frame["predicted_margin"]).abs(),
        data_frame["match__margin"] + data_frame["predicted_margin"],
    )


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
        .reset_index(level=GROUP_BY_LVL, drop=True)
    )


def _calculate_cumulative_margin_difference(data_frame: pd.DataFrame):
    return (
        data_frame.groupby("ml_model__name")
        .expanding()["absolute_margin_diff"]
        .sum()
        .reset_index(level=GROUP_BY_LVL, drop=True)
    )


def calculate_cumulative_metrics(
    metric_values: List[Dict[str, Any]], round_number: Optional[int]
) -> pd.DataFrame:
    """Calculate cumulative methods that can't be calculated via the ORM."""
    return (
        pd.DataFrame(metric_values)
        .astype({"predicted_margin": float, "predicted_win_probability": float})
        .sort_values("match__start_date_time")
        .assign(
            tip_point=lambda df: df["is_correct"].astype(int),
            absolute_margin_diff=_calculate_absolute_margin_difference,
            bits=_calculate_bits,
        )
        .assign(
            cumulative_correct_count=_calculate_cumulative_correct,
            cumulative_accuracy=_calculate_cumulative_accuracy,
            cumulative_margin_difference=_calculate_cumulative_margin_difference,
            cumulative_bits=_calculate_cumulative_bits,
            cumulative_mean_absolute_error=_calculate_cumulative_mae,
        )
        .fillna(0)
        .groupby(["match__round_number", "ml_model__name"])
        .last()
        .pipe(partial(_filter_by_round, round_number=round_number))
    )
