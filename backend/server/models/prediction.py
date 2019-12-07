"""Data model for ML predictions for AFL matches"""

from django.db import models, transaction
import numpy as np

from server.types import CleanPredictionData
from .match import Match
from .ml_model import MLModel
from .team import Team


class Prediction(models.Model):
    """Model for ML model predictions for each match"""

    match = models.ForeignKey(Match, on_delete=models.CASCADE)
    ml_model = models.ForeignKey(MLModel, on_delete=models.CASCADE)
    predicted_winner = models.ForeignKey(
        Team, on_delete=models.CASCADE, related_name="predicted_wins"
    )
    predicted_margin = models.PositiveSmallIntegerField()
    is_correct = models.BooleanField(default=False)

    @classmethod
    def update_or_create_from_data(cls, prediction_data: CleanPredictionData) -> None:
        """
        Convert raw prediction data to a Prediction model instance. Tries to find
        and update existing prediction for the given match/model combination,
        and creates new one if none is found.

        Args:
            prediction_data (CleanPredictionData): Dictionary that include
                prediction data for two teams that are playing each other
                in a given match.

        Returns:
            prediction (Prediction): Unsaved Prediction model instance.
        """

        home_team = prediction_data["home_team"]
        away_team = prediction_data["away_team"]

        home_margin = prediction_data["home_predicted_margin"]
        away_margin = prediction_data["away_predicted_margin"]

        # predicted_margin is always positive as its always associated with predicted_winner
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
        prediction_attributes = {"match": match, "ml_model": ml_model}

        with transaction.atomic():
            prediction, was_created = cls.objects.update_or_create(
                **prediction_attributes,
                defaults={
                    "predicted_margin": predicted_margin,
                    "predicted_winner": predicted_winner,
                },
            )

            if was_created:
                prediction.full_clean()
            else:
                prediction.clean()

            prediction.save()

    def clean(self):
        # Judgement call, but I want to avoid 0 predicted margin values for the cases
        # where the floating prediction is < 0.5, because we're never predicting a draw
        self.predicted_margin = round(self.predicted_margin) or 1

    def update_correctness(self):
        """Update the correct attribute based on associated team_match scores"""

        self.is_correct = self._calculate_whether_correct()
        self.full_clean()
        self.save()

    def _calculate_whether_correct(self) -> bool:
        """
        Calculate whether a prediction is correct based on match results
        and conventional footy-tipping rules.
        """

        # In footy tipping competitions its typical to grant everyone a correct tip
        # in the case of a draw
        return self.match.has_been_played and (
            self.match.is_draw or self.predicted_winner == self.match.winner
        )
