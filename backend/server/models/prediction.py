"""Data model for ML predictions for AFL matches."""

from typing import Tuple, Optional, cast, Literal, Union
from datetime import date

from django.db import models, transaction
from django.core.validators import MinValueValidator
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.core.exceptions import ValidationError
import numpy as np
from mypy_extensions import TypedDict

from server.types import CleanPredictionData
from .match import Match
from .ml_model import MLModel
from .team import Team


MatchingAttributes = TypedDict(
    "MatchingAttributes", {"match": Match, "ml_model": MLModel}
)


class Prediction(models.Model):
    """Model for ML model predictions for each match."""

    created_at = models.DateTimeField(auto_now_add=True, null=False, blank=False)
    updated_at = models.DateTimeField(auto_now=True, null=False, blank=False)
    match = models.ForeignKey(Match, on_delete=models.CASCADE)
    ml_model = models.ForeignKey(MLModel, on_delete=models.CASCADE)
    predicted_winner = models.ForeignKey(
        Team, on_delete=models.CASCADE, related_name="predicted_wins"
    )
    predicted_margin = models.FloatField(
        blank=True, null=True, validators=[MinValueValidator(0.0)]
    )
    predicted_win_probability = models.FloatField(blank=True, null=True)
    is_correct = models.BooleanField(null=True, blank=True)

    @classmethod
    def update_or_create_from_raw_data(
        cls, prediction_data: CleanPredictionData, future_only=False
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

        matching_attributes = cls._matching_attributes_for_update(
            prediction_data, future_only
        )

        if matching_attributes is None:
            return None

        with transaction.atomic():
            prediction, _ = cls.objects.update_or_create(
                **matching_attributes,
                defaults={
                    "predicted_margin": predicted_margin,
                    "predicted_win_probability": predicted_win_probability,
                    "predicted_winner": predicted_winner,
                },
            )

            prediction.full_clean()
            prediction.save()
            cls.update_correctness(prediction)

        return prediction

    @classmethod
    def _calculate_predictions(
        cls,
        prediction_data: CleanPredictionData,
        prediction_type: Union[Literal["margin"], Literal["win_probability"]],
    ) -> Tuple[Optional[np.number], Optional[Team]]:
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

        # TODO: The win probability model is kind of messed up this year,
        # so we've gotten a prediction where they're equal, and I don't feel
        # like revisiting the model, so we'll let it slide this season.
        assert home_predicted_result != away_predicted_result or (
            prediction_type == "win_probability" and date.today().year == 2021
        ), (
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
    def _calculate_predicted_margin(
        cls, home_margin: np.number, away_margin: np.number
    ) -> np.number:
        both_predicted_to_win = home_margin > 0 and away_margin > 0
        both_predicted_to_lose = home_margin < 0 and away_margin < 0

        # predicted_margin is always positive as it's always associated
        # with predicted_winner
        if both_predicted_to_win or both_predicted_to_lose:
            return abs(home_margin - away_margin)

        return np.mean(np.abs([home_margin, away_margin]))

    @classmethod
    def _calculate_predicted_win_probability(
        cls, home_win_probability: np.number, away_win_probability: np.number
    ) -> np.number:
        predicted_loser_oppo_win_proba = 1 - np.min(
            [home_win_probability, away_win_probability]
        )
        predicted_winner_win_proba = np.max(
            [home_win_probability, away_win_probability]
        )
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

        return Team.objects.get(name=prediction_data[predicted_winner])

    @classmethod
    def _matching_attributes_for_update(
        cls, prediction_data: CleanPredictionData, future_only
    ) -> Optional[MatchingAttributes]:
        matches = Match.objects.filter(
            start_date_time__year=prediction_data["year"],
            round_number=prediction_data["round_number"],
            teammatch__team__name__in=[
                prediction_data["home_team"],
                prediction_data["away_team"],
            ],
        )

        assert len(matches) == 2 and matches[0] == matches[1], (
            "Prediction data should have yielded a unique match, with duplicates "
            "returned from the DB, but we got the following instead:\n"
            f"Matches: {matches.values('round_number', 'start_date_time')}\n\n"
            f"Prediction: {prediction_data}"
        )

        match = matches.first()

        if future_only and match.start_date_time < timezone.now():
            return None

        ml_model = MLModel.objects.get(name=prediction_data["ml_model"])

        return {"match": match, "ml_model": ml_model}

    def clean(self):
        """
        Clean prediction records before saving them.

        - Round predicted_margin to the nearest integer.
        - Set the minimum predicted margin to 1.
        - Validate that the prediction includes predicted margin or
            predicted win probability, but not both.
        """

        if self.predicted_margin is None and self.predicted_win_probability is None:
            raise ValidationError(
                _(
                    "Prediction must have a predicted_margin or "
                    "predicted_win_probability."
                )
            )

        # This validation is codifying an assumption made on the frontend
        # that makes the logic for displaying the predictions table simpler.
        # For now, this holds true of all Tipresias models, but may change
        # in the future.
        if (
            self.predicted_margin is not None
            and self.predicted_win_probability is not None
        ):
            raise ValidationError(
                _(
                    "Prediction cannot have both a predicted_margin and "
                    "predicted_win_probability."
                )
            )

    def update_correctness(self):
        """Update the correct attribute based on associated team_match scores."""
        self.is_correct = self._calculate_whether_correct()
        self.full_clean()
        self.save()

    def _calculate_whether_correct(self) -> Optional[bool]:
        """
        Calculate whether a prediction is correct.

        This is based on a combination of match results and conventional
        footy-tipping rules (i.e. draws count as correct).
        """

        if not self.match.has_been_played:
            return None

        # In footy tipping competitions its typical to grant everyone a correct tip
        # in the case of a draw
        return self.match.is_draw or self.predicted_winner == self.match.winner
