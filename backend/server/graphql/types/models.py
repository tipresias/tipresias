"""GraphQL types for the Django DB models."""

import graphene
from graphene_django.types import DjangoObjectType

from server.models import Team, Prediction, Match, TeamMatch, MLModel


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

    year = graphene.Int(required=True)
    home_team = graphene.Field(TeamType)
    away_team = graphene.Field(TeamType)
    predictions = graphene.List(
        graphene.NonNull(PredictionType),
        ml_model_name=graphene.String(default_value=None),
        required=True,
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

    used_in_competitions = graphene.Boolean(
        description="Whether the model's predictions are used in any competitions.",
        required=True,
    )

    is_principal = graphene.Boolean(
        description=(
            "Whether the model is the principal model for predicting match winners "
            "among all the models used in competitions (i.e. all competition models "
            "predict winners, but only one's predictions are official "
            "predicted winners of Tipresias)."
        ),
        required=True,
    )
