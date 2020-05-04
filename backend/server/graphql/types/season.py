"""Match and prediction data grouped by season."""

from typing import List, cast, Optional
from functools import partial

from django.db.models import QuerySet
import graphene
import pandas as pd
from mypy_extensions import TypedDict

from server.models import MLModel
from server.types import RoundModelMetrics, MatchPredictions
from server.graphql import cumulative_calculations
from .models import MLModelType


ModelMetric = TypedDict(
    "ModelMetric",
    {
        "ml_model__name": str,
        "cumulative_correct_count": int,
        "cumulative_accuracy": float,
        "cumulative_mean_absolute_error": float,
        "cumulative_margin_difference": int,
        "cumulative_bits": float,
    },
)

RoundPredictions = TypedDict(
    "RoundPredictions", {"round_number": int, "match_predictions": QuerySet}
)


ML_MODEL_NAME_LVL = 0


class MatchPredictionType(graphene.ObjectType):
    """Official Tipresias predictions for a given match."""

    match__start_date_time = graphene.NonNull(graphene.DateTime, name="startDateTime")
    predicted_winner__name = graphene.NonNull(graphene.String, name="predictedWinner")
    predicted_margin = graphene.NonNull(graphene.Int)
    predicted_win_probability = graphene.NonNull(graphene.Float)
    is_correct = graphene.Boolean()


class RoundPredictionType(graphene.ObjectType):
    """Official Tipresias predictions for a given round."""

    round_number = graphene.NonNull(graphene.Int)
    match_predictions = graphene.List(
        graphene.NonNull(MatchPredictionType), required=True
    )

    @staticmethod
    def resolve_match_predictions(root: RoundPredictions, _info) -> MatchPredictions:
        """Return prediction data for matches in the given round."""

        return (
            pd.DataFrame(
                root["match_predictions"]
                .prefetch_related("match", "ml_model", "match__teammatch_set")
                .values(
                    "match__id",
                    "match__start_date_time",
                    "ml_model__is_principle",
                    "ml_model__used_in_competitions",
                    "predicted_winner__name",
                    "predicted_margin",
                    "predicted_win_probability",
                    "is_correct",
                )
            )
            .pipe(cumulative_calculations.consolidate_competition_predictions)
            .to_dict("records")
        )


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
        root: RoundModelMetrics, _info, ml_model_name=None, for_competition_only=False,
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
            root["model_metrics"]
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


def _group_data_by_round(data_frame: pd.DataFrame) -> List[RoundModelMetrics]:
    return [
        cast(
            RoundModelMetrics,
            {
                data_frame.index.names[
                    cumulative_calculations.ROUND_NUMBER_LVL
                ]: round_number_idx,
                "model_metrics": data_frame.xs(
                    round_number_idx, level=cumulative_calculations.ROUND_NUMBER_LVL
                ),
            },
        )
        for round_number_idx in data_frame.index.get_level_values(
            cumulative_calculations.ROUND_NUMBER_LVL
        ).drop_duplicates()
    ]


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
        metric_values = cumulative_calculations.query_database_for_prediction_metrics(
            prediction_query_set
        ).values(
            *cumulative_calculations.REQUIRED_VALUES_FOR_METRICS,
            "ml_model__used_in_competitions"
        )

        return (
            cumulative_calculations.calculate_cumulative_metrics(metric_values)
            .pipe(
                partial(
                    cumulative_calculations.filter_by_round, round_number=round_number
                )
            )
            .pipe(_group_data_by_round)
        )
