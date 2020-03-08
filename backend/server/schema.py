"""GraphQL schema for all queries."""

# TODO: Refactor the stats calculations. This may require some reorganising
# of the API itself, as there is quite a bit of similarity between stats-by-round
# and latest round stats.
# The main issue is that the queries and types are a little too specific.
# Consolidating the logic would require a little bit of processing on the frontend,
# but should reduce the overall complexity of the code.
from typing import List, cast, Optional

import graphene
from graphene_django.types import DjangoObjectType
from django.db.models import Count, Q, QuerySet
from django.utils import timezone
import pandas as pd
from mypy_extensions import TypedDict
import numpy as np

from server.models import Prediction, MLModel, TeamMatch, Match, Team


ModelPrediction = TypedDict(
    "ModelPrediction",
    {
        "ml_model__name": str,
        "cumulative_correct_count": int,
        "cumulative_accuracy": float,
        "cumulative_mean_absolute_error": float,
        "cumulative_margin_difference": int,
        "cumulative_bits": float,
    },
)

ModelStats = TypedDict(
    "ModelStats",
    {"model_stats": ModelPrediction, "round_number": int, "season_year": int},
)

RoundPrediction = TypedDict(
    "RoundPrediction",
    {
        "match__round_number": int,
        "model_predictions": List[ModelPrediction],
        "matches": QuerySet,
    },
)


# For regressors that might try to predict negative values or 0,
# we need a slightly positive minimum to not get errors when calculating logarithms
MIN_LOG_VAL = 1 * 10 ** -10


class TeamType(DjangoObjectType):
    """GraphQL type based on the Team data model."""

    class Meta:
        """For adding Django model attributes to their associated GraphQL types."""

        model = Team


class PredictionType(DjangoObjectType):
    """Basic prediction type based on the Prediction data model."""

    class Meta:
        """For adding Django model attributes to their associated GraphQL types."""

        model = Prediction


class MatchType(DjangoObjectType):
    """GraphQL type based on the Match data model."""

    class Meta:
        """For adding Django model attributes to their associated GraphQL types."""

        model = Match

    winner = graphene.Field(TeamType)
    year = graphene.Int()
    home_team = graphene.Field(TeamType)
    away_team = graphene.Field(TeamType)
    predictions = graphene.List(
        PredictionType, ml_model_name=graphene.String(default_value=None)
    )

    @staticmethod
    def resolve_predictions(root, _info, ml_model_name=None):
        """Return predictions for this match."""
        if ml_model_name is None:
            return root.prediction_set.all()

        return root.prediction_set.filter(ml_model__name=ml_model_name)

    @staticmethod
    def resolve_home_team(root, _info):
        """Return the home team for this match."""
        return root.teammatch_set.get(at_home=True).team

    @staticmethod
    def resolve_away_team(root, _info):
        """Return the away team for this match."""
        return root.teammatch_set.get(at_home=False).team


class TeamMatchType(DjangoObjectType):
    """GraphQL type based on the TeamMatch data model."""

    class Meta:
        """For adding Django model attributes to their associated GraphQL types."""

        model = TeamMatch


class MLModelType(DjangoObjectType):
    """GraphQL type based on the MLModel data model."""

    class Meta:
        """For adding Django model attributes to their associated GraphQL types."""

        model = MLModel


class CumulativePredictionsByRoundType(graphene.ObjectType):
    """
    Cumulative stats for predictions made by the given model through the given round.
    """

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


class RoundStatsType(graphene.ObjectType):
    """Cumulative model stats for a given season up to a given round."""

    season_year = graphene.Int()
    round_number = graphene.Int()
    model_stats = graphene.Field(CumulativePredictionsByRoundType)


class RoundType(graphene.ObjectType):
    """Match and prediction data for a given season grouped by round."""

    match__round_number = graphene.Int(name="roundNumber")
    model_predictions = graphene.List(
        CumulativePredictionsByRoundType,
        description=(
            "Cumulative stats for predictions made by the given model "
            "through the given round"
        ),
        default_value=pd.DataFrame(),
    )
    matches = graphene.List(MatchType, default_value=[])

    @staticmethod
    def resolve_model_predictions(root, _info) -> List[ModelPrediction]:
        """Calculate metrics related to the quality of models' predictions."""
        model_predictions_to_dict = lambda df: [
            {df.index.names[0]: value, **df.loc[value, :].to_dict()}
            for value in df.index
        ]

        prediction_dicts = root.get("model_predictions").pipe(model_predictions_to_dict)

        return [
            cast(ModelPrediction, model_prediction)
            for model_prediction in prediction_dicts
        ]


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
            description="Optional filter when only one round of data is required",
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
        query_set = (
            root.values("match__round_number", "ml_model__name")
            .order_by("match__round_number")
            .annotate(
                correct_count=Count("is_correct", filter=Q(is_correct=True)),
                match_count=Count("match"),
            )
        )

        # TODO: There's definitely a way to do these calculations via SQL, but chained
        # GROUP BYs and calculations based on calculations is a bit much for me
        # right now, so I'll come back and figure it out later
        calculate_cumulative_correct = lambda df: (
            df.groupby("ml_model__name")
            .expanding()
            .sum()
            .reset_index(level=0)["correct_count"]
            .rename("cumulative_correct_count")
        )

        calculate_cumulative_count = lambda df: (
            df.groupby("ml_model__name")
            .expanding()
            .sum()
            .reset_index(level=0, drop=True)["match_count"]
            .rename("cumulative_count")
        )

        collect_round_predictions = lambda df: [
            {
                df.index.names[0]: value,
                "model_predictions": df.xs(value, level=0),
                "matches": Match.objects.filter(
                    id__in=query_set.filter(match__round_number=value).values_list(
                        "match", flat=True
                    )
                ),
            }
            for value in df.index.levels[0]
        ]

        query_set_data_frame = pd.DataFrame(list(query_set))

        if round_number is not None:
            query_set_data_frame = query_set_data_frame.query(
                "match__round_number == @round_number"
            )

        round_predictions = (
            query_set_data_frame.assign(
                cumulative_correct_count=calculate_cumulative_correct,
                cumulative_match_count=calculate_cumulative_count,
                cumulative_accuracy=lambda df: (
                    (
                        df["cumulative_correct_count"] / df["cumulative_match_count"]
                    ).round(2)
                ),
            )
            .drop("cumulative_match_count", axis=1)
            .groupby(["match__round_number", "ml_model__name"])
            .mean()
        )

        return round_predictions.pipe(collect_round_predictions)


class Query(graphene.ObjectType):
    """Base GraphQL Query type that contains all queries and their resolvers."""

    fetch_predictions = graphene.List(
        PredictionType, year=graphene.Int(default_value=None)
    )

    fetch_prediction_years = graphene.List(
        graphene.Int,
        description="All years for which model predictions exist in the database",
    )

    fetch_yearly_predictions = graphene.Field(
        SeasonType, year=graphene.Int(default_value=timezone.localtime().year)
    )

    fetch_latest_round_predictions = graphene.Field(
        RoundType,
        description=(
            "Match info and predictions for the latest round for which data "
            "is available"
        ),
    )

    fetch_latest_round_stats = graphene.Field(
        RoundStatsType,
        description="Cumulative model prediction stats for the latest season.",
        ml_model_name=graphene.String(default_value="tipresias_2019"),
    )

    @staticmethod
    def resolve_fetch_predictions(_root, _info, year=None) -> QuerySet:
        """Return all predictions from the given year or from all years."""
        if year is None:
            return Prediction.objects.all()

        return Prediction.objects.filter(match__start_date_time__year=year)

    @staticmethod
    def resolve_fetch_prediction_years(_root, _info) -> List[int]:
        """Return all years for which we have prediction data."""
        return (
            Prediction.objects.select_related("match")
            .distinct("match__start_date_time__year")
            .order_by("match__start_date_time__year")
            .values_list("match__start_date_time__year", flat=True)
        )

    @staticmethod
    def resolve_fetch_yearly_predictions(_root, _info, year) -> QuerySet:
        """Return all predictions from the given year."""
        return Prediction.objects.filter(
            match__start_date_time__year=year
        ).select_related("ml_model", "match")

    @staticmethod
    def resolve_fetch_latest_round_predictions(_root, _info) -> RoundPrediction:
        """Return predictions and model metrics for the latest available round."""
        max_match = Match.objects.order_by("-start_date_time").first()

        matches = (
            Match.objects.filter(
                start_date_time__year=max_match.start_date_time.year,
                round_number=max_match.round_number,
            )
            .prefetch_related("prediction_set", "teammatch_set")
            .order_by("start_date_time")
        )

        return {
            "match__round_number": max_match.round_number,
            "model_predictions": pd.DataFrame(),
            "matches": matches,
        }

    @staticmethod
    def resolve_fetch_latest_round_stats(_root, _info, ml_model_name) -> ModelStats:
        """Calculate model performance metrics through the latest round."""
        max_played_match = (
            Match.objects.filter(start_date_time__lt=timezone.localtime())
            .order_by("-start_date_time")
            .first()
        )
        max_year = max_played_match.start_date_time.year

        query_set = (
            Prediction.objects.filter(
                match__start_date_time__year=max_year,
                ml_model__name=ml_model_name,
                match__start_date_time__lt=timezone.localtime(),
            )
            .select_related("match", "ml_model")
            .order_by("match__start_date_time")
            .annotate(correct_count=Count("is_correct", filter=Q(is_correct=True)))
        )

        assert query_set.count() > 0, (
            "Could not find records for the latest round. Check that there are matches "
            f"in {max_year}, that {ml_model_name} has predictions for that year, "
            f"and that there are match records after {timezone.localtime()}"
        )

        prediction_data = []

        for prediction in query_set:
            match = prediction.match

            if match.winner is None:
                continue

            prediction_data.append(
                {
                    "match__round_number": match.round_number,
                    "ml_model__name": prediction.ml_model.name,
                    "predicted_margin": prediction.predicted_margin,
                    "predicted_win_probability": prediction.predicted_win_probability,
                    "predicted_winner__name": prediction.predicted_winner.name,
                    "correct_count": prediction.correct_count,
                    "winner": match.winner.name,
                    "margin": match.margin,
                }
            )

        prediction_df = pd.DataFrame(prediction_data)

        calculate_margin_diff = lambda df: (
            df["predicted_margin"]
            + (
                df["margin"]
                # We want to subtract margins if correct winner was predicted,
                # add margins otherwise
                * (df["predicted_winner__name"] == df["winner"]).apply(
                    lambda x: -1 if x else 1
                )
            )
        ).abs()

        # TODO: There's definitely a way to do these calculations via SQL, but chained
        # GROUP BYs and calculations based on calculations is a bit much for me
        # right now, so I'll come back and figure it out later
        calculate_cumulative_correct = lambda df: (
            df.expanding()["correct_count"].sum().rename("cumulative_correct_count")
        )

        calculate_cumulative_accuracy = lambda df: (
            df.expanding()["correct_count"]
            .mean()
            .round(2)
            .rename("cumulative_accuracy")
        )

        calculate_sae = lambda df: (
            df.expanding()["margin_diff"].sum().rename("cumulative_margin_difference")
        )

        calculate_mae = lambda df: (
            df.expanding()["margin_diff"]
            .mean()
            .round(2)
            .rename("cumulative_mean_absolute_error")
        )

        positive_pred = lambda y_pred: (
            np.maximum(y_pred, np.repeat(MIN_LOG_VAL, len(y_pred)))
        )
        draw_bits = lambda y_pred: (
            1 + (0.5 * np.log2(positive_pred(y_pred * (1 - y_pred))))
        )
        win_bits = lambda y_pred: 1 + np.log2(positive_pred(y_pred))
        loss_bits = lambda y_pred: 1 + np.log2(positive_pred(1 - y_pred))

        # Raw bits calculations per http://probabilistic-footy.monash.edu/~footy/about.shtml
        calculate_bits = lambda df: np.where(
            df["margin"] == 0,
            draw_bits(df["predicted_win_probability"]),
            np.where(
                df["winner"] == df["predicted_winner__name"],
                win_bits(df["predicted_win_probability"]),
                loss_bits(df["predicted_win_probability"]),
            ),
        )

        calculate_cumulative_bits = lambda df: (
            df.expanding()["bits"].sum().rename("cumulative_bits")
        )

        cumulative_stats = (
            prediction_df.fillna(0)
            .assign(
                cumulative_correct_count=calculate_cumulative_correct,
                cumulative_accuracy=calculate_cumulative_accuracy,
                margin_diff=calculate_margin_diff,
                bits=calculate_bits,
            )
            .assign(
                cumulative_margin_difference=calculate_sae,
                cumulative_bits=calculate_cumulative_bits,
            )
            .assign(cumulative_mean_absolute_error=calculate_mae)
        )

        last_cumulative_stats = cumulative_stats.iloc[-1, :]

        return {
            "season_year": max_year,
            "round_number": last_cumulative_stats["match__round_number"],
            "model_stats": last_cumulative_stats.to_dict(),
        }


schema = graphene.Schema(query=Query)
