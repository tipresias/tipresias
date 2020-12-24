"""Data model for AFL predictions."""

from __future__ import annotations
from typing import Optional, Dict, Any

from cerberus import Validator, TypeDefinition
from mypy_extensions import TypedDict

from .match import Match
from .ml_model import MLModel
from .team import Team
from .base_model import BaseModel, ValidationError


PredictionAttributes = TypedDict(
    "PredictionAttributes",
    {
        "match": Match,
        "ml_model": MLModel,
        "predicted_winner": Team,
        "predicted_margin": float,
        "predicted_win_probability": float,
        "was_correct": bool,
    },
    total=False,
)


class Prediction(BaseModel):
    """Data model for predictions."""

    PREDICTION_TYPES = ("margin", "win_probability")

    def __init__(  # pylint: disable=too-many-arguments
        self,
        match: Optional[Match] = None,
        ml_model: Optional[MLModel] = None,
        predicted_winner: Optional[Team] = None,
        predicted_margin: Optional[float] = None,
        predicted_win_probability: Optional[float] = None,
        was_correct: Optional[bool] = None,
    ):
        """
        Params:
        -------
        match: Match for which the prediction is made.
        ml_model: The ML model that made the prediction.
        predicted_winner: The team that is predicted to win the match.
        predicted_margin: Number of points by which the predicted winner
            is predicted to win by.
        predicted_win_probability: The expected probability of the predicted winner
            actually winning.
        was_correct: Whether the predicted winner actually won.
        """
        match_type = TypeDefinition("match", (Match,), ())
        Validator.types_mapping["match"] = match_type
        team_type = TypeDefinition("team", (Team,), ())
        Validator.types_mapping["team"] = team_type
        ml_model_type = TypeDefinition("ml_model", (MLModel,), ())
        Validator.types_mapping["ml_model"] = ml_model_type

        super().__init__(Validator)

        self.match = match
        self.ml_model = ml_model
        self.predicted_winner = predicted_winner
        self.predicted_margin = predicted_margin
        self.predicted_win_probability = predicted_win_probability
        self.was_correct = was_correct

    @classmethod
    def from_db_response(cls, record: Dict[str, Any]) -> Prediction:
        """Convert a DB record object into an instance of Prediction.

        Params:
        -------
        record: GraphQL response dictionary that represents the prediction record.

        Returns:
        --------
        A Prediction with the attributes of the prediction record.
        """
        match = Match.from_db_response(record["match"])
        ml_model = MLModel.from_db_response(record["mlModel"])
        predicted_winner = Team.from_db_response(record["predictedWinner"])
        prediction = Prediction(
            match=match,
            ml_model=ml_model,
            predicted_winner=predicted_winner,
            predicted_margin=record["predictedMargin"],
            predicted_win_probability=record["predictedWinProbability"],
            was_correct=record["wasCorrect"],
        )
        prediction.id = record["_id"]

        return prediction

    def create(self) -> Prediction:
        """Create the prediction in the DB."""
        self.validate()

        query = """
            mutation(
                $matchId: ID!,
                $mlModelId: ID!,
                $predictedWinnerId: ID!,
                $predictedMargin: Float,
                $predictedWinProbability: Float,
                $wasCorrect: Boolean
            ) {
                createPrediction(data: {
                    match: { connect: $matchId },
                    mlModel: { connect: $mlModelId },
                    predictedWinner: { connect: $predictedWinnerId },
                    predictedMargin: $predictedMargin,
                    predictedWinProbability: $predictedWinProbability,
                    wasCorrect: $wasCorrect
                }) {
                    _id
                }
            }
        """
        variables = {
            "matchId": self.match and self.match.id,
            "mlModelId": self.ml_model and self.ml_model.id,
            "predictedWinnerId": self.predicted_winner and self.predicted_winner.id,
            "predictedMargin": self.predicted_margin,
            "predictedWinProbability": self.predicted_win_probability,
            "wasCorrect": self.was_correct,
        }

        result = self.db_client().graphql(query, variables)
        self.id = result["createPrediction"]["_id"]

        return self

    def update(self, **attribute_kwargs) -> Prediction:
        """Update the prediction in the DB."""
        if self.id is None:
            raise ValidationError("must have an ID")

        for key, value in attribute_kwargs.items():
            setattr(self, key, value)

        self.validate()

        query = """
            mutation(
                $id: ID!,
                $matchId: ID!,
                $mlModelId: ID!,
                $predictedWinnerId: ID!,
                $predictedMargin: Float,
                $predictedWinProbability: Float,
                $wasCorrect: Boolean
            ) {
                updatePrediction(
                    id: $id,
                    data: {
                        match: { connect: $matchId },
                        mlModel: { connect: $mlModelId },
                        predictedWinner: { connect: $predictedWinnerId },
                        predictedMargin: $predictedMargin,
                        predictedWinProbability: $predictedWinProbability,
                        wasCorrect: $wasCorrect
                    }
                ) {
                    _id
                }
            }
        """
        variables = {
            "id": self.id,
            "matchId": self.match and self.match.id,
            "mlModelId": self.ml_model and self.ml_model.id,
            "predictedWinnerId": self.predicted_winner and self.predicted_winner.id,
            "predictedMargin": self.predicted_margin,
            "predictedWinProbability": self.predicted_win_probability,
            "wasCorrect": self.was_correct,
        }

        self.db_client().graphql(query, variables)

        return self

    @property
    def _schema(self):
        return {
            "match": {"type": "match", "check_with": self._idfulness},
            "ml_model": {"type": "ml_model", "check_with": self._idfulness},
            "predicted_winner": {"type": "team", "check_with": self._idfulness},
            "predicted_margin": {"type": "float", "min": 0.0, "nullable": True},
            "predicted_win_probability": {
                "type": "float",
                "min": 0.0,
                "nullable": True,
            },
            "was_correct": {"type": "boolean", "nullable": True},
        }

    @staticmethod
    def _idfulness(field, value, error):
        if value and value.id is None:
            error(field, "must have an ID")
