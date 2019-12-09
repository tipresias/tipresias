from datetime import datetime

from django.test import TestCase
from django.utils import timezone
from django.core.exceptions import ValidationError
import pandas as pd

from server.models import Match, MLModel, Team, Prediction
from server.helpers import pivot_team_matches_to_matches
from server.tests.fixtures.data_factories import fake_prediction_data


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

    def test_convert_data_to_record(self):
        data = fake_prediction_data(self.match, ml_model_name=self.ml_model.name)
        home_away_df = pivot_team_matches_to_matches(pd.DataFrame(data))

        self.assertEqual(Prediction.objects.count(), 0)
        Prediction.update_or_create_from_raw_data(home_away_df.to_dict("records")[0])
        self.assertEqual(Prediction.objects.count(), 1)

        with self.subTest("when prediction record already exists"):
            predicted_margin = 100
            home_away_df.loc[:, "home_predicted_margin"] = predicted_margin
            home_away_df.loc[:, "away_predicted_margin"] = -predicted_margin

            Prediction.update_or_create_from_raw_data(home_away_df.to_dict("records")[0])
            self.assertEqual(Prediction.objects.count(), 1)

            prediction = Prediction.objects.first()
            self.assertEqual(prediction.predicted_margin, predicted_margin)

        # Regression tests for bug that caused update_or_create_from_raw_data
        # to select wrong team as predicted_winner when predicted margin
        # was greater than away team's predicted winning margin
        with self.subTest(
            "when predicted margins are skewed with large home losing margin"
        ):
            predicted_winning_margin = 100
            predicted_losing_margin = -200
            home_away_df.loc[:, "home_predicted_margin"] = predicted_losing_margin
            home_away_df.loc[:, "away_predicted_margin"] = predicted_winning_margin

            Prediction.update_or_create_from_raw_data(home_away_df.to_dict("records")[0])
            prediction = Prediction.objects.first()
            self.assertEqual(prediction.predicted_margin, 150)
            self.assertEqual(
                home_away_df["away_team"].iloc[0], prediction.predicted_winner.name
            )

        with self.subTest(
            "when predicted margins are skewed with large away losing margin"
        ):
            predicted_winning_margin = 100
            predicted_losing_margin = -200
            home_away_df.loc[:, "home_predicted_margin"] = predicted_winning_margin
            home_away_df.loc[:, "away_predicted_margin"] = predicted_losing_margin

            Prediction.update_or_create_from_raw_data(home_away_df.to_dict("records")[0])
            prediction = Prediction.objects.first()
            self.assertEqual(prediction.predicted_margin, 150)
            self.assertEqual(
                home_away_df["home_team"].iloc[0], prediction.predicted_winner.name
            )

        with self.subTest("when predicted margins are less than 0.5"):
            predicted_winning_margin = 0.4
            predicted_losing_margin = -0.4
            home_away_df.loc[:, "home_predicted_margin"] = predicted_winning_margin
            home_away_df.loc[:, "away_predicted_margin"] = predicted_losing_margin

            Prediction.update_or_create_from_raw_data(home_away_df.to_dict("records")[0])
            prediction = Prediction.objects.first()
            self.assertEqual(prediction.predicted_margin, 1)
            self.assertEqual(
                home_away_df["home_team"].iloc[0], prediction.predicted_winner.name
            )

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

    def test_update_correctness(self):
        with self.subTest("when higher-scoring team is predicted winner"):
            prediction = Prediction(
                match=self.match,
                ml_model=self.ml_model,
                predicted_winner=self.home_team,
                predicted_margin=50,
            )
            prediction.update_correctness()

            self.assertTrue(prediction.is_correct)

        with self.subTest("when lower-scoring team is predicted winner"):
            prediction = Prediction(
                match=self.match,
                ml_model=self.ml_model,
                predicted_winner=self.away_team,
                predicted_margin=50,
            )
            prediction.update_correctness()

            self.assertFalse(prediction.is_correct)

        with self.subTest("when match is a draw"):
            self.match.teammatch_set.update(score=100)
            prediction = Prediction(
                match=self.match,
                ml_model=self.ml_model,
                predicted_winner=self.away_team,
                predicted_margin=50,
            )
            prediction.update_correctness()

            self.assertTrue(prediction.is_correct)
