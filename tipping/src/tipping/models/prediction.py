"""Data model for AFL predictions."""

from __future__ import annotations
from typing import Optional, Dict, Any, Union, Literal, cast, Tuple
from datetime import datetime, timezone

from cerberus import Validator, TypeDefinition
from mypy_extensions import TypedDict
import numpy as np
import pandas as pd

from .match import Match
from .ml_model import MLModel
from .team import Team
from .base_model import BaseModel, ValidationError


MatchingAttributes = TypedDict(
    "MatchingAttributes", {"match": Match, "ml_model": MLModel}
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
    def from_db_response(  # pylint: disable=arguments-differ
        cls, record: Dict[str, Any], match: Optional[Match] = None
    ) -> Prediction:
        """Convert a DB record object into an instance of Prediction.

        Params:
        -------
        record: GraphQL response dictionary that represents the prediction record.

        Returns:
        --------
        A Prediction with the attributes of the prediction record.
        """
        match = match or Match.from_db_response(record["match"])
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

    @classmethod
    def update_or_create_from_raw_data(
        cls, prediction_data: pd.Series, future_only=False
    ) -> Optional["Prediction"]:
        """
        Convert raw prediction data to a Prediction model instance.

        Tries to find and update existing prediction for the given
        match/model combination, and creates new one if none is found.

        Params:
        -------
        prediction_data: Dictionary that include prediction data for two teams
            that are playing each other in a given match.

        Returns:
        --------
            Unsaved Prediction model instance.
        """
        predicted_margin, predicted_margin_winner = cls._calculate_predictions(
            prediction_data, "margin"
        )
        (
            predicted_win_probability,
            predicted_proba_winner,
        ) = cls._calculate_predictions(prediction_data, "win_probability")

        # For now, each estimator predicts margins or win probabilities, but not both.
        # If we eventually have an estimator that predicts both, we're defaulting
        # to the predicted winner by margin, but we may want to revisit this
        predicted_winner = predicted_margin_winner or predicted_proba_winner

        assert predicted_winner is not None, (
            "Each prediction should have a predicted_winner:\n" f"{prediction_data}"
        )

        match, ml_model = cls._matching_relations_for_update(
            prediction_data, future_only
        )

        if (match is None) or (ml_model is None):
            return None

        match_ml_model_name = (
            lambda prediction: prediction.ml_model.name == ml_model.name
        )

        matching_predictions = filter(
            match_ml_model_name,
            match.predictions,
        )

        try:
            prediction = next(matching_predictions)
            prediction.update(
                predicted_margin=predicted_margin,
                predicted_win_probability=predicted_win_probability,
                predicted_winner=predicted_winner,
            )
        except StopIteration:
            prediction = Prediction(
                match=match,
                ml_model=ml_model,
                predicted_margin=predicted_margin,
                predicted_win_probability=predicted_win_probability,
                predicted_winner=predicted_winner,
            )
            prediction.create()

        prediction.update_correctness()

        return prediction

    def update_correctness(self) -> Prediction:
        """Update the was_correct attribute based on associated team_match scores."""
        self.was_correct = self._calculate_whether_correct()
        return self.update()

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

    @classmethod
    def _calculate_predictions(
        cls,
        prediction_data: pd.Series,
        prediction_type: Union[Literal["margin"], Literal["win_probability"]],
    ) -> Tuple[Optional[float], Optional[Team]]:
        home_prediction_key = cast(
            Union[
                Literal["home_predicted_margin"],
                Literal["home_predicted_win_probability"],
            ],
            f"home_predicted_{prediction_type}",
        )
        away_prediction_key = cast(
            Union[
                Literal["away_predicted_margin"],
                Literal["away_predicted_win_probability"],
            ],
            f"away_predicted_{prediction_type}",
        )

        home_predicted_result = prediction_data[home_prediction_key]
        away_predicted_result = prediction_data[away_prediction_key]

        if home_predicted_result is None or away_predicted_result is None:
            return None, None

        assert home_predicted_result != away_predicted_result, (
            "Home and away predictions are equal, which is basically impossible, "
            "so figure out what's going on:\n"
            f"{prediction_data}"
        )

        predicted_result = (
            cls._calculate_predicted_margin(
                home_predicted_result, away_predicted_result
            )
            if prediction_type == "margin"
            else cls._calculate_predicted_win_probability(
                home_predicted_result, away_predicted_result
            )
        )

        return predicted_result, cls._calculate_predicted_winner(
            prediction_data, home_predicted_result, away_predicted_result
        )

    @classmethod
    def _calculate_predicted_margin(cls, home_margin, away_margin) -> float:
        both_predicted_to_win = home_margin > 0 and away_margin > 0
        both_predicted_to_lose = home_margin < 0 and away_margin < 0

        # predicted_margin is always positive as it's always associated
        # with predicted_winner
        if both_predicted_to_win or both_predicted_to_lose:
            return abs(home_margin - away_margin)

        return np.mean(np.abs([home_margin, away_margin]))

    @classmethod
    def _calculate_predicted_win_probability(
        cls, home_win_probability, away_win_probability
    ) -> float:
        predicted_loser_oppo_win_proba = 1 - min(
            [home_win_probability, away_win_probability]
        )
        predicted_winner_win_proba = max([home_win_probability, away_win_probability])
        predicted_win_probability = np.mean(
            [predicted_loser_oppo_win_proba, predicted_winner_win_proba]
        )

        return predicted_win_probability

    @classmethod
    def _calculate_predicted_winner(
        cls, prediction_data, home_predicted_result, away_predicted_result
    ) -> Team:
        predicted_winner = (
            "home_team"
            if home_predicted_result > away_predicted_result
            else "away_team"
        )

        team = Team.find_by(name=prediction_data[predicted_winner])

        assert team is not None

        return team

    @classmethod
    def _matching_relations_for_update(
        cls, prediction_data: pd.Series, future_only
    ) -> Tuple[Optional[Match], Optional[MLModel]]:
        matches_by_team_names = lambda match: {
            team_match.team and team_match.team.name
            for team_match in match.team_matches
        } == {
            prediction_data["home_team"],
            prediction_data["away_team"],
        }

        matches = list(
            filter(
                matches_by_team_names,
                Match.filter_by_season(season=prediction_data["year"]).filter(
                    round_number=prediction_data["round_number"]
                ),
            )
        )

        assert len(matches) == 1, (
            "Prediction data should have yielded a unique match, but we got "
            "the following instead:\n"
            f"Matches: {[match.attributes for match in matches]}\n\n"
            f"Prediction: {prediction_data}"
        )

        match = matches[0]

        if future_only and match.start_date_time < datetime.now(tz=timezone.utc):
            return None, None

        ml_model = MLModel.find_by_name(name=prediction_data["ml_model"])

        assert ml_model is not None

        return match, ml_model

    def _calculate_whether_correct(self) -> Optional[bool]:
        """
        Calculate whether a prediction is correct.

        This is based on a combination of match results and conventional
        footy-tipping rules (i.e. draws count as correct).
        """
        assert self.match

        if not self.match.has_been_played:
            return None

        # In footy tipping competitions its typical to grant everyone a correct tip
        # in the case of a draw
        return self.match.is_draw or bool(
            self.predicted_winner
            and self.match.winner
            and self.predicted_winner.id == self.match.winner.id
        )
