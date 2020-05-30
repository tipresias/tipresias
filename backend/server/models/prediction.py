"""Data model for ML predictions for AFL matches."""

from typing import Tuple, Optional

from django.db import models, transaction
from django.core.validators import MinValueValidator
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError
import numpy as np

from server.types import CleanPredictionData
from .match import Match
from .ml_model import MLModel
from .team import Team


class Prediction(models.Model):
    """Model for ML model predictions for each match."""

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
        cls, prediction_data: CleanPredictionData
    ) -> None:
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
        home_team = prediction_data["home_team"]
        away_team = prediction_data["away_team"]

        predicted_margin, predicted_margin_winner = cls._calculate_predicted_margin(
            prediction_data, home_team, away_team
        )
        (
            predicted_win_probability,
            predicted_proba_winner,
        ) = cls._calculate_predicted_win_probability(  # pylint: disable=line-too-long
            prediction_data, home_team, away_team
        )

        # For now, each estimator predicts margins or win probabilities, but not both.
        # If we eventually have an estimator that predicts both, we're defaulting
        # to the predicted winner by margin, but we may want to revisit this
        predicted_winner = predicted_margin_winner or predicted_proba_winner

        assert predicted_winner is not None, (
            "Each prediction should have a predicted_winner:\n" f"{prediction_data}"
        )

        matches = Match.objects.filter(
            start_date_time__year=prediction_data["year"],
            round_number=prediction_data["round_number"],
            teammatch__team__name__in=[home_team, away_team],
        )

        if len(matches) != 2 or matches[0] != matches[1]:
            raise ValueError(
                "Prediction data should have yielded a unique match, with duplicates "
                "returned from the DB, but we got the following instead:\n"
                f"{matches.values('round_number', 'start_date_time')}\n\n"
                f"{prediction_data}"
            )

        match = matches.first()
        ml_model = MLModel.objects.get(name=prediction_data["ml_model"])
        matching_prediction_attributes = {"match": match, "ml_model": ml_model}

        with transaction.atomic():
            prediction, _ = cls.objects.update_or_create(
                **matching_prediction_attributes,
                defaults={
                    "predicted_margin": predicted_margin,
                    "predicted_win_probability": predicted_win_probability,
                    "predicted_winner": predicted_winner,
                },
            )

            prediction.full_clean()
            prediction.save()
            cls.update_correctness(prediction)

    @classmethod
    def _calculate_predicted_margin(
        cls, prediction_data: CleanPredictionData, home_team, away_team
    ) -> Tuple[Optional[float], Optional[str]]:
        home_margin = prediction_data["home_predicted_margin"]
        away_margin = prediction_data["away_predicted_margin"]

        if home_margin is None or away_margin is None:
            return None, None

        # predicted_margin is always positive as it's always associated
        # with predicted_winner
        if (home_margin > 0 and away_margin > 0) or (
            home_margin < 0 and away_margin < 0
        ):
            predicted_margin = abs(home_margin - away_margin)
        else:
            predicted_margin = np.mean(np.abs([home_margin, away_margin]))

        if home_margin > away_margin:
            predicted_winner = Team.objects.get(name=home_team)
        elif away_margin > home_margin:
            predicted_winner = Team.objects.get(name=away_team)
        else:
            raise ValueError(
                "Predicted home and away margins are equal, which is basically "
                "impossible, so figure out what's going on:\n"
                f"{prediction_data}"
            )

        return predicted_margin, predicted_winner

    @classmethod
    def _calculate_predicted_win_probability(
        cls, prediction_data: CleanPredictionData, home_team, away_team
    ) -> Tuple[Optional[float], Optional[str]]:
        home_probability = prediction_data["home_predicted_win_probability"]
        away_probability = prediction_data["away_predicted_win_probability"]

        if home_probability is None or away_probability is None:
            return None, None

        assert home_probability != away_probability, (
            "Predicted home and away win probabilities are equal, "
            "which is basically impossible, so figure out what's going on:\n"
            f"{prediction_data}"
        )

        predicted_loser_oppo_win_proba = 1 - min([home_probability, away_probability])
        predicted_winner_win_proba = max([home_probability, away_probability])
        predicted_win_probability = np.mean(
            [predicted_loser_oppo_win_proba, predicted_winner_win_proba]
        )

        predicted_winner_name = (
            home_team if home_probability > away_probability else away_team
        )
        predicted_winner = Team.objects.get(name=predicted_winner_name)

        return predicted_win_probability, predicted_winner

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

        if self.predicted_margin is not None:
            # Judgement call, but I want to avoid 0 predicted margin values
            # for the cases where the floating prediction is < 0.5,
            # because we're never predicting a draw
            self.predicted_margin = round(self.predicted_margin) or 1

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
