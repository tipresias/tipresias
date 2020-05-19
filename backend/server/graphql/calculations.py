"""Module for shared logic for calculating model metrics."""

from typing import Optional, List

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

from server.models import TeamMatch


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


def cumulative_metrics_query(
    prediction_query_set: QuerySet, additional_values: Optional[List[str]] = None,
):
    """
    Chain methods onto a Prediction query set to calculate cumulative model metrics.
    """
    values_args = CUMULATIVE_METRICS_VALUES + (additional_values or [])

    return (
        prediction_query_set.select_related("ml_model", "match")
        .order_by("match__start_date_time")
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
        .values(*values_args)
    )
