from functools import reduce
from datetime import datetime, timedelta

from django.db import models, transaction
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from sklearn.externals import joblib
import numpy as np

from machine_learning.ml_estimators import BaseMLEstimator
from machine_learning.data_config import TEAM_NAMES
from project.settings.common import MELBOURNE_TIMEZONE
from server.types import CleanPredictionData

# Rough estimate, but exactitude isn't necessary here
GAME_LENGTH_HRS = 3


def validate_name(name: str) -> None:
    if name in TEAM_NAMES:
        return None

    raise ValidationError(_("%(name)s is not a valid team name"), params={"name": name})


def validate_module_path(path: str) -> None:
    if "." in path and "/" not in path:
        return None

    raise ValidationError(
        _(
            "%(path)s is not a valid module path. Be sure to separate modules & classes "
            "with a '.'"
        ),
        params={"path": path},
    )


class Team(models.Model):
    name = models.CharField(max_length=100, unique=True, validators=[validate_name])


class Match(models.Model):
    start_date_time = models.DateTimeField()
    round_number = models.PositiveSmallIntegerField()
    venue = models.CharField(max_length=100, null=True, blank=True)

    class Meta:
        unique_together = ("start_date_time", "venue")

    @property
    def is_draw(self):
        return self.has_been_played and reduce(
            lambda score_x, score_y: score_x == score_y, self.__match_scores
        )

    @property
    def winner(self):
        if not self.has_been_played or self.is_draw:
            return None

        return max(self.teammatch_set.all(), key=lambda tm: tm.score).team

    @property
    def year(self):
        return self.start_date_time.year

    @property
    def has_been_played(self):
        match_end_time = self.start_date_time + timedelta(hours=GAME_LENGTH_HRS)

        # We need to check the scores in case the data hasn't been updated since the
        # match was played, because as far as the data is concerned it hasn't, even though
        # the date has passed.
        return self.__has_score and match_end_time < datetime.now(MELBOURNE_TIMEZONE)

    @property
    def __has_score(self):
        return any([score > 0 for score in self.__match_scores])

    @property
    def __match_scores(self):
        return self.teammatch_set.all().values_list("score", flat=True)


class TeamMatch(models.Model):
    team = models.ForeignKey(Team, on_delete=models.CASCADE)
    match = models.ForeignKey(Match, on_delete=models.CASCADE)
    at_home = models.BooleanField()
    score = models.PositiveSmallIntegerField(default=0)


class MLModel(models.Model):
    trained_to_match = models.ForeignKey(
        Match, on_delete=models.SET_NULL, null=True, blank=True
    )
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(null=True, blank=True)
    filepath = models.CharField(max_length=500, null=True, blank=True)
    data_class_path = models.CharField(
        max_length=500, null=True, blank=True, validators=[validate_module_path]
    )

    def load_estimator(self) -> BaseMLEstimator:
        return joblib.load(self.filepath)


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
    def calculate_whether_correct(cls, match: Match, predicted_winner: Team) -> bool:
        """
        Calculate if a prediction is correct. Implemented as a class method to allow
        for one-step creation of new prediction records.

        Args:
            match (Match): Match data model
            predicted_winner (Team): Team data model for the team
                that's predicted to win

        Returns:
            bool
        """

        # In footy tipping competitions its typical to grant everyone a correct tip
        # in the case of a draw
        return match.has_been_played and (
            match.is_draw or predicted_winner == match.winner
        )

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

        if predicted_margin > away_margin:
            predicted_winner = Team.objects.get(name=home_team)
        elif away_margin > predicted_margin:
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

    def clean(self):
        # Judgement call, but I want to avoid 0 predicted margin values for the cases
        # where the floating prediction is < 0.5, because we're never predicting a draw
        self.predicted_margin = round(self.predicted_margin) or 1
