from datetime import datetime
from django.test import TestCase
from django.utils import timezone
from django.core.exceptions import ValidationError

from server.models import Match, MLModel, Team, Prediction


class TestPrediction(TestCase):
    def setUp(self):
        match_datetime = timezone.make_aware(datetime(2018, 5, 5))
        self.match = Match.objects.create(
            start_date_time=match_datetime, round_number=5, venue="Corporate Stadium"
        )
        self.ml_model = MLModel.objects.create(name="test_model")

        self.home_team = Team.objects.create(name="Richmond")
        self.away_team = Team.objects.create(name="Melbourne")

        self.match.teammatch_set.create(team=self.home_team, at_home=True, score=150)
        self.match.teammatch_set.create(team=self.away_team, at_home=False, score=100)

    def test_is_correct(self):
        with self.subTest("when higher-scoring team is predicted winner"):
            prediction = Prediction(
                match=self.match,
                ml_model=self.ml_model,
                predicted_winner=self.home_team,
                predicted_margin=50,
            )
            self.assertTrue(prediction.is_correct)

        with self.subTest("when lower-scoring team is predicted winner"):
            prediction = Prediction(
                match=self.match,
                ml_model=self.ml_model,
                predicted_winner=self.away_team,
                predicted_margin=50,
            )
            self.assertFalse(prediction.is_correct)

        with self.subTest("when match is a draw"):
            self.match.teammatch_set.update(score=100)
            prediction = Prediction(
                match=self.match,
                ml_model=self.ml_model,
                predicted_winner=self.away_team,
                predicted_margin=50,
            )

            self.assertTrue(prediction.is_correct)

    def test_clean(self):
        with self.subTest("when predicted margin rounds to 0"):
            prediction = Prediction(
                match=self.match,
                ml_model=self.ml_model,
                predicted_winner=self.away_team,
                predicted_margin=0.2,
            )

            prediction.clean()
            self.assertEqual(1, prediction.predicted_margin)

        with self.subTest("when predicted margin is a float"):
            prediction = Prediction(
                match=self.match,
                ml_model=self.ml_model,
                predicted_winner=self.away_team,
                predicted_margin=65.7,
            )

            prediction.clean()
            self.assertEqual(66, prediction.predicted_margin)

    def test_validation(self):
        with self.subTest("when predicted margin is negative"):
            prediction = Prediction(
                match=self.match,
                ml_model=self.ml_model,
                predicted_winner=self.away_team,
                predicted_margin=-50,
            )

            with self.assertRaises(ValidationError):
                prediction.full_clean()
