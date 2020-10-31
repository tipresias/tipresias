"""Match and prediction data grouped by season."""

from typing import List, cast, Optional, Callable
from functools import partial
from datetime import datetime

from django.db.models import QuerySet
import graphene
import pandas as pd
import numpy as np
from mypy_extensions import TypedDict

from server.models import MLModel
from server.graphql.calculations import calculate_cumulative_metrics
from .models import MLModelType


ModelMetric = TypedDict(
    "ModelMetric",
    {
        "ml_model__name": str,
        "cumulative_correct_count": int,
        "cumulative_accuracy": float,
        "cumulative_mean_absolute_error": float,
        "cumulative_margin_difference": float,
        "cumulative_bits": float,
    },
)

RoundModelMetrics = TypedDict(
    "RoundModelMetrics",
    {"match__round_number": int, "model_metrics": pd.DataFrame},
)

RoundPredictions = TypedDict(
    "RoundPredictions", {"round_number": int, "match_predictions": QuerySet}
)

MatchPredictions = TypedDict(
    "MatchPredictions",
    {
        "match__start_date_time": datetime,
        "predicted_winner__name": str,
        "predicted_margin": int,
        "predicted_win_probability": float,
        "is_correct": bool,
    },
)


ML_MODEL_NAME_LVL = 0
# For regressors that might try to predict negative values or 0,
# we need a slightly positive minimum to not get errors when calculating logarithms
MIN_LOG_VAL = 1 * 10 ** -10

ROUND_NUMBER_LVL = 0
GROUP_BY_LVL = 0


class MatchPredictionType(graphene.ObjectType):
    """Official Tipresias predictions for a given match."""

    match__start_date_time = graphene.NonNull(graphene.DateTime, name="startDateTime")
    predicted_winner__name = graphene.NonNull(graphene.String, name="predictedWinner")
    predicted_margin = graphene.NonNull(graphene.Float)
    predicted_win_probability = graphene.NonNull(graphene.Float)
    is_correct = graphene.Boolean()


def _invert_contradicting_predictions(
    non_principal_prediction_label: str,
) -> Callable[[pd.DataFrame], np.array]:
    if non_principal_prediction_label == "predicted_margin":
        invert_values = lambda arr: arr * -1
    else:
        invert_values = lambda arr: 1 - arr

    return lambda df: np.where(
        df["predictions_agree"],
        df[non_principal_prediction_label],
        invert_values(df[non_principal_prediction_label]),
    )


class RoundPredictionType(graphene.ObjectType):
    """Official Tipresias predictions for a given round."""

    round_number = graphene.NonNull(graphene.Int)
    match_predictions = graphene.List(
        graphene.NonNull(MatchPredictionType), required=True
    )

    @staticmethod
    def resolve_match_predictions(root: RoundPredictions, _info) -> MatchPredictions:
        """Return prediction data for matches in the given round."""

        predictions = pd.DataFrame(
            root["match_predictions"]
            .prefetch_related("match", "ml_model", "match__teammatch_set")
            .values(
                "match__id",
                "match__start_date_time",
                "ml_model__is_principal",
                "predicted_winner__name",
                "predicted_margin",
                "predicted_win_probability",
                "is_correct",
            )
        ).sort_values("match__start_date_time")

        principal_predictions = predictions.query(
            "ml_model__is_principal == True"
        ).set_index("match__id")
        non_principal_predictions = (
            predictions.query("ml_model__is_principal == False")
            .fillna(0)
            .set_index("match__id")
            .loc[
                :,
                [
                    "predicted_winner__name",
                    "predicted_margin",
                    "predicted_win_probability",
                ],
            ]
        )

        non_principal_prediction_type = MLModel.objects.get(
            is_principal=False, used_in_competitions=True
        ).prediction_type
        non_principal_prediction_label = "predicted_" + (
            non_principal_prediction_type.lower().replace(" ", "_")
        )

        competition_predictions = (
            principal_predictions.fillna(non_principal_predictions)
            .assign(
                predictions_agree=lambda df: df["predicted_winner__name"]
                == non_principal_predictions["predicted_winner__name"]
            )
            .assign(
                **{
                    f"{non_principal_prediction_label}": _invert_contradicting_predictions(
                        non_principal_prediction_label
                    )
                }
            )
            .replace({np.nan: None})
            .to_dict("records")
        )

        return competition_predictions


class SeasonPerformanceChartParametersType(graphene.ObjectType):
    """
    Parameters for displaying info and populating inputs for the performance chart.
    """

    available_seasons = graphene.List(
        graphene.NonNull(graphene.Int),
        description=(
            "All season years for which model predictions exist in the database"
        ),
        required=True,
    )

    available_ml_models = graphene.List(
        graphene.NonNull(MLModelType),
        description="All ML models that have predictions in the database.",
        required=True,
    )


class ModelMetricsByRoundType(graphene.ObjectType):
    """Performance metrics for the given model through the given round."""

    ml_model = graphene.NonNull(MLModelType)
    cumulative_correct_count = graphene.Int(
        description=(
            "Cumulative sum of correct tips made by the given model "
            "for the given season"
        ),
        default_value=0,
        required=True,
    )
    cumulative_accuracy = graphene.Float(
        description=(
            "Cumulative mean of correct tips (i.e. accuracy) made by the given model "
            "for the given season."
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
    def resolve_ml_model(root, _info):
        """Fetch MLModel record based on requested MLModel name."""

        return MLModel.objects.get(name=root["ml_model__name"])


def _filter_by_model(
    data_frame: pd.DataFrame,
    ml_model_name: Optional[str] = None,
    for_competition_only: bool = False,
) -> pd.DataFrame:
    name_filter = slice(ml_model_name) if ml_model_name is None else [ml_model_name]

    competition_query = "(ml_model__used_in_competitions == True)"

    if not for_competition_only:
        competition_query = (
            competition_query + " | (ml_model__used_in_competitions == False)"
        )

    return data_frame.query(competition_query).loc[name_filter, :]


class RoundType(graphene.ObjectType):
    """Match and prediction data for a given season grouped by round."""

    match__round_number = graphene.NonNull(graphene.Int, name="roundNumber")
    model_metrics = graphene.List(
        graphene.NonNull(ModelMetricsByRoundType),
        description=(
            "Performance metrics for predictions made by the given model "
            "through the given round"
        ),
        ml_model_name=graphene.String(
            description="Get predictions and metrics for a specific ML model",
        ),
        for_competition_only=graphene.Boolean(
            default_value=False,
            description=(
                "Only get prediction metrics for ML models used in competitions"
            ),
        ),
        required=True,
    )

    @staticmethod
    def resolve_model_metrics(
        root,
        _info,
        ml_model_name=None,
        for_competition_only=False,
    ) -> List[ModelMetric]:
        """Calculate metrics related to the quality of models' predictions."""
        model_metrics_to_dict = lambda df: [
            {
                df.index.names[ML_MODEL_NAME_LVL]: ml_model_name_idx,
                **df.loc[ml_model_name_idx, :].to_dict(),
            }
            for ml_model_name_idx in df.index
        ]

        metric_dicts = (
            root.get("model_metrics")
            .pipe(
                partial(
                    _filter_by_model,
                    ml_model_name=ml_model_name,
                    for_competition_only=for_competition_only,
                )
            )
            .drop("ml_model__used_in_competitions", axis=1)
            .pipe(model_metrics_to_dict)
        )

        return [cast(ModelMetric, model_metrics) for model_metrics in metric_dicts]


def _collect_data_by_round(data_frame: pd.DataFrame) -> List[RoundModelMetrics]:
    return [
        cast(
            RoundModelMetrics,
            {
                data_frame.index.names[ROUND_NUMBER_LVL]: round_number_idx,
                "model_metrics": data_frame.xs(
                    round_number_idx, level=ROUND_NUMBER_LVL
                ),
            },
        )
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


class SeasonType(graphene.ObjectType):
    """Model performance metrics grouped by season."""

    season = graphene.NonNull(graphene.Int)

    round_model_metrics = graphene.List(
        graphene.NonNull(RoundType),
        description="Model performance metrics grouped by round",
        round_number=graphene.Int(
            description=(
                "Optional filter when only one round of data is required. "
                "-1 will return the last available round."
            ),
        ),
        required=True,
    )

    @staticmethod
    def resolve_season(prediction_query_set, _info) -> int:
        """Return the year for the given season."""
        # Have to use list indexing to get first instead of .first(),
        # because the latter raises a weird SQL error
        return prediction_query_set.distinct("match__start_date_time__year")[
            0
        ].match.start_date_time.year

    @staticmethod
    def resolve_round_model_metrics(
        prediction_query_set, _info, round_number: Optional[int] = None
    ) -> List[RoundModelMetrics]:
        """Return model performance metrics for the season grouped by round."""

        metric_values = (
            prediction_query_set.select_related("ml_model", "match")
            # We don't want to include matches without results, which would impact
            # mean-based metrics like accuracy and MAE
            .filter(match__margin__isnull=False).values(
                "match__margin",
                "match__round_number",
                "match__start_date_time",
                "match__winner__name",
                "ml_model__name",
                "ml_model__used_in_competitions",
                "predicted_margin",
                "predicted_winner__name",
                "predicted_win_probability",
                "is_correct",
            )
        )

        return calculate_cumulative_metrics(metric_values, round_number).pipe(
            _collect_data_by_round
        )
