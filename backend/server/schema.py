from typing import List, cast, Optional
from datetime import datetime
import pytz

import graphene
from graphene_django.types import DjangoObjectType
from django.db.models import Count, Q, QuerySet
import pandas as pd
from mypy_extensions import TypedDict

from server.models import Prediction, MLModel, TeamMatch, Match, Team


ModelPrediction = TypedDict(
    "ModelPrediction",
    {
        "ml_model__name": str,
        "cumulative_correct_count": int,
        "cumulative_mean_absolute_error": float,
        "cumulative_margin_difference": int,
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


class TeamType(DjangoObjectType):
    class Meta:
        model = Team


class PredictionType(DjangoObjectType):
    """Basic prediction type based on Prediction data model"""

    class Meta:
        model = Prediction


class MatchType(DjangoObjectType):
    class Meta:
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
        if ml_model_name is None:
            return root.prediction_set.all()

        return root.prediction_set.filter(ml_model__name=ml_model_name)

    @staticmethod
    def resolve_home_team(root, _info):
        return root.teammatch_set.get(at_home=True).team

    @staticmethod
    def resolve_away_team(root, _info):
        return root.teammatch_set.get(at_home=False).team


class TeamMatchType(DjangoObjectType):
    class Meta:
        model = TeamMatch


class MLModelType(DjangoObjectType):
    class Meta:
        model = MLModel


class CumulativePredictionsByRoundType(graphene.ObjectType):
    """
    Cumulative stats for predictions made by the given model through the given round
    """

    ml_model__name = graphene.String(name="modelName")
    cumulative_correct_count = graphene.Int(
        description=(
            "Cumulative sum of correct tips made by the given model "
            "for the given season"
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


class RoundStatsType(graphene.ObjectType):
    """Cumulative model stats for a given season up to a given round"""

    season_year = graphene.Int()
    round_number = graphene.Int()
    model_stats = graphene.Field(CumulativePredictionsByRoundType)


class RoundType(graphene.ObjectType):
    """Match and prediction data for a given season grouped by round"""

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
    """Match and prediction data grouped by season"""

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
        # Have to use list indexing to get first instead of .first(),
        # because the latter raises a weird SQL error
        return root.distinct("match__start_date_time__year")[
            0
        ].match.start_date_time.year

    @staticmethod
    def resolve_prediction_model_names(root, _info) -> List[str]:
        return root.distinct("ml_model__name").values_list("ml_model__name", flat=True)

    @staticmethod
    def resolve_predictions_by_round(
        root, _info, round_number: Optional[int] = None
    ) -> List[RoundPrediction]:
        query_set = (
            root.values("match__round_number", "ml_model__name")
            .order_by("match__round_number")
            .annotate(correct_count=Count("is_correct", filter=Q(is_correct=True)))
        )

        # TODO: There's definitely a way to do these calculations via SQL, but chained
        # GROUP BYs and calculations based on calculations is a bit much for me
        # right now, so I'll come back and figure it out later
        calculate_cumulative_correct = (
            lambda df: df.groupby("ml_model__name")
            .expanding()
            .sum()
            .reset_index(level=0)["correct_count"]
            .rename("cumulative_correct_count")
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
                cumulative_correct_count=calculate_cumulative_correct
            )
            .groupby(["match__round_number", "ml_model__name"])
            .mean()
        )

        return round_predictions.pipe(collect_round_predictions)


class Query(graphene.ObjectType):
    fetch_predictions = graphene.List(
        PredictionType, year=graphene.Int(default_value=None)
    )

    fetch_prediction_years = graphene.List(
        graphene.Int,
        description="All years for which model predictions exist in the database",
    )

    fetch_yearly_predictions = graphene.Field(
        SeasonType, year=graphene.Int(default_value=datetime.now(tz=pytz.UTC).year)
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
        ml_model_name=graphene.String(default_value="tipresias"),
    )

    @staticmethod
    def resolve_fetch_predictions(_root, _info, year=None) -> QuerySet:
        if year is None:
            return Prediction.objects.all()

        return Prediction.objects.filter(match__start_date_time__year=year)

    @staticmethod
    def resolve_fetch_prediction_years(_root, _info) -> List[int]:
        return (
            Prediction.objects.select_related("match")
            .distinct("match__start_date_time__year")
            .order_by("match__start_date_time__year")
            .values_list("match__start_date_time__year", flat=True)
        )

    @staticmethod
    def resolve_fetch_yearly_predictions(_root, _info, year) -> QuerySet:
        return Prediction.objects.filter(
            match__start_date_time__year=year
        ).select_related("ml_model", "match")

    @staticmethod
    def resolve_fetch_latest_round_predictions(_root, _info) -> RoundPrediction:
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
        max_played_match = (
            Match.objects.filter(start_date_time__lt=datetime.now(tz=pytz.UTC))
            .order_by("-start_date_time")
            .first()
        )
        max_year = max_played_match.start_date_time.year

        query_set = (
            Prediction.objects.filter(
                match__start_date_time__year=max_year,
                ml_model__name=ml_model_name,
                match__start_date_time__lt=datetime.now(tz=pytz.UTC),
            )
            .select_related("match", "ml_model")
            .order_by("match__start_date_time")
            .annotate(correct_count=Count("is_correct", filter=Q(is_correct=True)))
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
                    "predicted_winner__name": prediction.predicted_winner.name,
                    "correct_count": prediction.correct_count,
                    "winner": match.winner.name,
                    "margin": match.margin,
                }
            )

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
        calculate_cumulative_correct = (
            lambda df: df.expanding()["correct_count"]
            .sum()
            .rename("cumulative_correct_count")
        )

        calculate_sae = (
            lambda df: df.expanding()["margin_diff"]
            .sum()
            .rename("cumulative_margin_difference")
        )

        calculate_mae = (
            lambda df: df.expanding()["margin_diff"]
            .mean()
            .round(2)
            .rename("cumulative_mean_absolute_error")
        )

        cumulative_stats = (
            pd.DataFrame(prediction_data)
            .assign(
                cumulative_correct_count=calculate_cumulative_correct,
                margin_diff=calculate_margin_diff,
            )
            .assign(cumulative_margin_difference=calculate_sae)
            .assign(cumulative_mean_absolute_error=calculate_mae)
        )

        last_cumulative_stats = cumulative_stats.iloc[-1, :]

        return {
            "season_year": max_year,
            "round_number": last_cumulative_stats["match__round_number"],
            "model_stats": last_cumulative_stats.to_dict(),
        }


schema = graphene.Schema(query=Query)
