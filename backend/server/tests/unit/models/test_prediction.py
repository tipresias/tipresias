import os
import sys
from datetime import datetime
from django.test import TestCase
from django.utils import timezone

from server.models import Match, MLModel, Team, Prediction, TeamMatch


class TestPrediction(TestCase):
    def setUp(self):
        match_datetime = timezone.make_aware(datetime(2018, 5, 5))
        self.match = Match(start_date_time=match_datetime, round_number=5)
        self.match.save()

        self.ml_model = MLModel(name="test_model")
        self.ml_model.save()

        self.home_team = Team(name="Richmond")
        self.home_team.save()
        self.away_team = Team(name="Melbourne")
        self.away_team.save()
        (
            TeamMatch(
                team=self.home_team, match=self.match, at_home=True, score=150
            ).save()
        )
        (
            TeamMatch(
                team=self.away_team, match=self.match, at_home=False, score=100
            ).save()
        )

    def test_is_correct(self):
        with self.subTest(predicted_winner=self.home_team):
            prediction = Prediction(
                match=self.match,
                ml_model=self.ml_model,
                predicted_winner=self.home_team,
                predicted_margin=50,
            )
            self.assertTrue(prediction.is_correct)

        with self.subTest(predicted_winner=self.away_team):
            prediction = Prediction(
                match=self.match,
                ml_model=self.ml_model,
                predicted_winner=self.away_team,
                predicted_margin=50,
            )
            self.assertFalse(prediction.is_correct)
