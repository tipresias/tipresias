"""Match and prediction data grouped by season."""

from typing import List, cast, Optional
from functools import partial

from django.utils import timezone
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
import graphene
import pandas as pd
import numpy as np

from server.types import ModelMetric, RoundPrediction
from server.models import TeamMatch, Match
from .models import MatchType

ML_MODEL_NAME_LVL = 0
# For regressors that might try to predict negative values or 0,
# we need a slightly positive minimum to not get errors when calculating logarithms
MIN_LOG_VAL = 1 * 10 ** -10

ROUND_NUMBER_LVL = 0
GROUP_BY_LVL = 0


class CumulativeMetricsByRoundType(graphene.ObjectType):
    """Cumulative performance metrics for the given model through the given round."""

    ml_model__name = graphene.String(name="modelName")
    cumulative_correct_count = graphene.Int(
        description=(
            "Cumulative sum of correct tips made by the given model "
            "for the given season"
        ),
        default_value=0,
    )
    cumulative_accuracy = graphene.Float(
        description=(
            "Cumulative mean of correct tips (i.e. accuracy) made by the given model "
            "for the given season."
        ),
        default_value=0,
    )
    cumulative_mean_absolute_error = graphene.Float(
        description="Cumulative mean absolute error for the given season",
        default_value=0,
    )
    cumulative_margin_difference = graphene.Int(
        description=(
            "Cumulative difference between predicted margin and actual margin "
            "for the given season."
        ),
        default_value=0,
    )
    cumulative_bits = graphene.Float(
        description="Cumulative bits metric for the given season.", default_value=0
    )


class RoundType(graphene.ObjectType):
    """Match and prediction data for a given season grouped by round."""

    match__round_number = graphene.Int(name="roundNumber")
    model_metrics = graphene.List(
        CumulativeMetricsByRoundType,
        description=(
            "Cumulative performance metrics for predictions made by the given model "
            "through the given round"
        ),
        default_value=pd.DataFrame(),
        ml_model_name=graphene.String(
            default_value=None,
            description="Get predictions and metrics for a specific ML model",
        ),
    )
    matches = graphene.List(MatchType, default_value=[])

    @staticmethod
    def resolve_model_metrics(root, _info, ml_model_name=None) -> List[ModelMetric]:
        """Calculate metrics related to the quality of models' predictions."""
        model_metrics_to_dict = lambda df: [
            {
                df.index.names[ML_MODEL_NAME_LVL]: ml_model_name_idx,
                **df.loc[ml_model_name_idx, :].to_dict(),
            }
            for ml_model_name_idx in df.index
            if ml_model_name is None or ml_model_name_idx == ml_model_name
        ]

        metric_dicts = root.get("model_metrics").pipe(model_metrics_to_dict)

        return [cast(ModelMetric, model_metrics) for model_metrics in metric_dicts]


def _collect_data_by_round(query_set: QuerySet, data_frame: pd.DataFrame):
    return [
        {
            data_frame.index.names[ROUND_NUMBER_LVL]: round_number_idx,
            "model_metrics": data_frame.xs(round_number_idx, level=ROUND_NUMBER_LVL),
            "matches": Match.objects.filter(
                id__in=query_set.filter(
                    match__round_number=round_number_idx
                ).values_list("match", flat=True)
            ),
        }
        for round_number_idx in data_frame.index.get_level_values(
            ROUND_NUMBER_LVL
        ).drop_duplicates()
    ]


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


class SeasonType(graphene.ObjectType):
    """Match and prediction data grouped by season."""

    season_year = graphene.Int()

    prediction_model_names = graphene.List(
        graphene.String, description="All model names available for the given year"
    )
    predictions_by_round = graphene.List(
        RoundType,
        description="Match and prediction data grouped by round",
        round_number=graphene.Int(
            default_value=None,
            description=(
                "Optional filter when only one round of data is required. "
                "-1 will return the last available round."
            ),
        ),
    )

    @staticmethod
    def resolve_season_year(root, _info) -> int:
        """Return the year for the given season."""
        # Have to use list indexing to get first instead of .first(),
        # because the latter raises a weird SQL error
        return root.distinct("match__start_date_time__year")[
            0
        ].match.start_date_time.year

    @staticmethod
    def resolve_prediction_model_names(root, _info) -> List[str]:
        """Return the names of all models that have predictions for the given season."""
        return root.distinct("ml_model__name").values_list("ml_model__name", flat=True)

    @staticmethod
    def resolve_predictions_by_round(
        root, _info, round_number: Optional[int] = None
    ) -> List[RoundPrediction]:
        """Return predictions for the season grouped by round."""
        sorted_query_set = root.order_by("match__start_date_time")

        query_set = (
            sorted_query_set
            # We don't want to include unplayed matches, which would impact
            # mean-based metrics like accuracy and MAE
            .filter(match__start_date_time__lt=timezone.localtime())
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
            )
        )

        return (
            pd.DataFrame(query_set)
            .fillna(0)
            .assign(bits=_calculate_bits)
            .assign(
                cumulative_margin_difference=_calculate_cumulative_margin_difference,
                cumulative_bits=_calculate_cumulative_bits,
                cumulative_mean_absolute_error=_calculate_cumulative_mae,
            )
            .groupby(["match__round_number", "ml_model__name"])
            .mean()
            .pipe(partial(_filter_by_round, round_number=round_number))
            .pipe(partial(_collect_data_by_round, sorted_query_set))
        )
