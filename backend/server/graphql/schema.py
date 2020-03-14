"""GraphQL schema for all queries."""

from typing import List

import graphene
from django.db.models import QuerySet
from django.utils import timezone
import pandas as pd

from server.models import Prediction, Match
from server.types import RoundPrediction
from .types import SeasonType, PredictionType, RoundType


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
        SeasonType,
        year=graphene.Int(
            default_value=timezone.localtime().year,
            description=("Filter results by year."),
        ),
    )

    fetch_latest_round_predictions = graphene.Field(
        RoundType,
        description=(
            "Match info and predictions for the latest round for which data "
            "is available"
        ),
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
            "model_metrics": pd.DataFrame(),
            "matches": matches,
        }
