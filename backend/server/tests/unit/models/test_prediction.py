# pylint: disable=missing-docstring
from datetime import datetime, timedelta

from django.test import TestCase
from django.utils import timezone
from django.core.exceptions import ValidationError

from server.models import Match, MLModel, Team, Prediction
from server.tests.fixtures.data_factories import fake_prediction_data


class TestPrediction(TestCase):
    def setUp(self):
        match_datetime = timezone.make_aware(datetime(2018, 5, 5))
        self.match = Match.objects.create(
            start_date_time=match_datetime, round_number=5, venue="Corporate Stadium"
        )
        self.ml_model = MLModel.objects.create(name="test_model")

        self.home_team = Team.create(name="Richmond")
        self.away_team = Team.create(name="Melbourne")

        self.match.teammatch_set.create(team=self.home_team, at_home=True, score=150)
        self.match.teammatch_set.create(team=self.away_team, at_home=False, score=100)

    def test_update_or_create_from_raw_data(self):
        data = fake_prediction_data(self.match, ml_model_name=self.ml_model.name)

        with self.subTest("when future_only is True"):
            with self.subTest("and the match has already been played"):
                self.assertLess(self.match.start_date_time, timezone.now())
                self.assertEqual(Prediction.objects.count(), 0)

                Prediction.update_or_create_from_raw_data(
                    data.to_dict("records")[0], future_only=True
                )

                # It doesn't create a prediction
                self.assertEqual(Prediction.objects.count(), 0)

            with self.subTest("and the match hasn't been played yet"):
                future_match = Match.objects.create(
                    start_date_time=(timezone.now() + timedelta(days=1)),
                    round_number=5,
                    venue="Corporate Stadium",
                )
                future_home_team = Team.create(name="Collingwood")
                future_away_team = Team.create(name="GWS")

                future_match.teammatch_set.create(
                    team=future_home_team, at_home=True, score=0
                )
                future_match.teammatch_set.create(
                    team=future_away_team, at_home=False, score=0
                )

                future_data = fake_prediction_data(
                    future_match, ml_model_name=self.ml_model.name
                )

                Prediction.update_or_create_from_raw_data(
                    future_data.to_dict("records")[0], future_only=True
                )

                # It creates a prediction
                self.assertEqual(Prediction.objects.count(), 1)

        Prediction.objects.all().delete()
        self.assertEqual(Prediction.objects.count(), 0)
        Prediction.update_or_create_from_raw_data(data.to_dict("records")[0])
        self.assertEqual(Prediction.objects.count(), 1)

        prediction = Prediction.objects.first()
        self.assertIsInstance(prediction.predicted_margin, float)
        self.assertIsNone(prediction.predicted_win_probability)

        with self.subTest("when prediction record already exists"):
            predicted_margin = 100
            data.loc[:, "home_predicted_margin"] = predicted_margin
            data.loc[:, "away_predicted_margin"] = -predicted_margin

            Prediction.update_or_create_from_raw_data(data.to_dict("records")[0])
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
            data.loc[:, "home_predicted_margin"] = predicted_losing_margin
            data.loc[:, "away_predicted_margin"] = predicted_winning_margin

            Prediction.update_or_create_from_raw_data(data.to_dict("records")[0])
            prediction = Prediction.objects.first()
            self.assertEqual(prediction.predicted_margin, 150)
            self.assertEqual(
                data["away_team"].iloc[0], prediction.predicted_winner.name
            )

        with self.subTest(
            "when predicted margins are skewed with large away losing margin"
        ):
            predicted_winning_margin = 100
            predicted_losing_margin = -200
            data.loc[:, "home_predicted_margin"] = predicted_winning_margin
            data.loc[:, "away_predicted_margin"] = predicted_losing_margin

            Prediction.update_or_create_from_raw_data(data.to_dict("records")[0])
            prediction = Prediction.objects.first()
            self.assertEqual(prediction.predicted_margin, 150)
            self.assertEqual(
                data["home_team"].iloc[0], prediction.predicted_winner.name
            )

        with self.subTest("when predicted margins are less than 0.5"):
            predicted_winning_margin = 0.4
            predicted_losing_margin = -0.4
            data.loc[:, "home_predicted_margin"] = predicted_winning_margin
            data.loc[:, "away_predicted_margin"] = predicted_losing_margin

            Prediction.update_or_create_from_raw_data(data.to_dict("records")[0])
            prediction = Prediction.objects.first()
            self.assertEqual(prediction.predicted_margin, 0.4)
            self.assertEqual(
                data["home_team"].iloc[0], prediction.predicted_winner.name
            )

        with self.subTest("when predicted margins are both positive"):
            predicted_winning_margin = 20.6
            predicted_losing_margin = 10.6
            data.loc[:, "home_predicted_margin"] = predicted_winning_margin
            data.loc[:, "away_predicted_margin"] = predicted_losing_margin

            Prediction.update_or_create_from_raw_data(data.to_dict("records")[0])
            prediction = Prediction.objects.first()
            self.assertEqual(prediction.predicted_margin, 10)
            self.assertEqual(
                data["home_team"].iloc[0], prediction.predicted_winner.name
            )

        with self.subTest("when predicted margins are both negative"):
            predicted_winning_margin = -10.6
            predicted_losing_margin = -20.6
            data.loc[:, "home_predicted_margin"] = predicted_winning_margin
            data.loc[:, "away_predicted_margin"] = predicted_losing_margin

            Prediction.update_or_create_from_raw_data(data.to_dict("records")[0])
            prediction = Prediction.objects.first()
            self.assertEqual(prediction.predicted_margin, 10)
            self.assertEqual(
                data["home_team"].iloc[0], prediction.predicted_winner.name
            )

        with self.subTest("when the calculated predicted_margin rounds up"):
            predicted_winning_margin = 5.8
            predicted_losing_margin = -5.7
            data.loc[:, "home_predicted_margin"] = predicted_winning_margin
            data.loc[:, "away_predicted_margin"] = predicted_losing_margin

            Prediction.update_or_create_from_raw_data(data.to_dict("records")[0])
            prediction = Prediction.objects.first()
            self.assertEqual(prediction.predicted_margin, 5.75)
            self.assertEqual(
                data["home_team"].iloc[0], prediction.predicted_winner.name
            )

        with self.subTest("when predicting win probability"):
            proba_data = fake_prediction_data(
                self.match, ml_model_name=self.ml_model.name, predict_margin=False
            )

            Prediction.update_or_create_from_raw_data(proba_data.to_dict("records")[0])

            prediction = Prediction.objects.first()
            self.assertIsInstance(prediction.predicted_win_probability, float)
            self.assertIsNone(prediction.predicted_margin)

    def test_clean(self):
        with self.subTest("when predicted margin and win probability are None"):
            prediction = Prediction(
                match=self.match,
                ml_model=self.ml_model,
                predicted_winner=self.away_team,
                predicted_margin=None,
                predicted_win_probability=None,
            )

            with self.assertRaisesMessage(
                ValidationError,
                "Prediction must have a predicted_margin or predicted_win_probability.",
            ):
                prediction.clean()

        with self.subTest("when predicted margin and win probability are both numbers"):
            prediction = Prediction(
                match=self.match,
                ml_model=self.ml_model,
                predicted_winner=self.away_team,
                predicted_margin=23,
                predicted_win_probability=0.23,
            )

            with self.assertRaisesMessage(
                ValidationError,
                "Prediction cannot have both a predicted_margin and "
                "predicted_win_probability.",
            ):
                prediction.clean()

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

        with self.subTest("when match hasn't been played yet"):
            match_datetime = timezone.make_aware(datetime.today() + timedelta(days=5))
            unplayed_match = Match.objects.create(
                start_date_time=match_datetime,
                round_number=5,
                venue="Corporate Stadium",
            )
            prediction = Prediction(
                match=unplayed_match,
                ml_model=self.ml_model,
                predicted_winner=self.away_team,
                predicted_margin=50,
            )
            prediction.update_correctness()

            self.assertEqual(prediction.is_correct, None)
