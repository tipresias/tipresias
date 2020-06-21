# pylint: disable=missing-docstring
from typing import Tuple
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock

from django.test import TestCase
from django.utils import timezone
from freezegun import freeze_time
import pandas as pd
from faker import Faker

from data.tipping import Tipper, FootyTipsSubmitter
from server.models import Match, TeamMatch, Prediction, MLModel
from server.tests.fixtures.data_factories import fake_fixture_data, fake_prediction_data
from server.tests.fixtures.factories import (
    TeamFactory,
    FullMatchFactory,
    PredictionFactory,
    MLModelFactory,
)


ROW_COUNT = 5
TIP_DATES = [
    timezone.make_aware(datetime(2016, 1, 1)),
    timezone.make_aware(datetime(2017, 1, 1)),
    timezone.make_aware(datetime(2018, 1, 1)),
]
FAKE = Faker()


class TestTipper(TestCase):
    @patch("data.data_import")
    def setUp(self, mock_data_import):  # pylint: disable=arguments-differ
        self.ml_model = MLModelFactory(
            name="test_estimator", is_principal=True, used_in_competitions=True
        )

        (
            self.fixture_return_values,
            prediction_return_values,
            match_results_return_values,
        ) = zip(
            *[self._build_imported_data_mocks(tip_date) for tip_date in TIP_DATES[:2]]
        )

        # We have 2 subtests in 2016 and 1 in 2017, which requires 3 fixture
        # and prediction data imports, but only 1 match results data import,
        # because it doesn't get called until 2017
        mock_data_import.fetch_prediction_data = Mock(
            side_effect=prediction_return_values[:1] + prediction_return_values
        )
        mock_data_import.fetch_fixture_data = Mock(
            side_effect=self.fixture_return_values[:1] + self.fixture_return_values
        )
        mock_data_import.fetch_match_results_data = Mock(
            return_value=match_results_return_values[0]
        )

        self.tipping = Tipper(data_importer=mock_data_import, verbose=0,)

    @patch("server.api.update_match_data")
    def test_update_match_data(self, mock_api_update_match_data):
        with freeze_time(TIP_DATES[0]):
            right_now = timezone.localtime()
            self.tipping._right_now = right_now  # pylint: disable=protected-access

            self.assertEqual(Match.objects.count(), 0)
            self.assertEqual(TeamMatch.objects.count(), 0)

            self.tipping.update_match_data()

            # It passes fixture data to server.api
            future_fixture_data = self.fixture_return_values[0].query(
                "date > @right_now"
            )
            min_future_round = future_fixture_data["round_number"].min()
            mock_api_update_match_data.assert_called_with(
                future_fixture_data.to_dict("records"), min_future_round
            )

        with freeze_time(TIP_DATES[1]):
            with self.subTest("with scoreless matches from ealier rounds"):
                right_now = timezone.localtime()
                self.tipping._right_now = right_now  # pylint: disable=protected-access

                self.assertEqual(TeamMatch.objects.filter(score__gt=0).count(), 0)
                self.assertEqual(Prediction.objects.filter(is_correct=True).count(), 0)

                self.tipping.update_match_data()

                # It updates scores for past matches
                self.assertEqual(
                    TeamMatch.objects.filter(
                        match__start_date_time__lt=right_now, score=0
                    ).count(),
                    0,
                )

        with freeze_time(TIP_DATES[2]):
            mock_api_update_match_data.reset_mock()

            with self.subTest("with no future matches"):
                right_now = timezone.localtime()
                self.tipping._right_now = right_now  # pylint: disable=protected-access

                self.tipping.update_match_data()

                mock_api_update_match_data.assert_not_called()

    def test_update_or_create_predictions(self):
        with freeze_time(TIP_DATES[0]):
            right_now = timezone.localtime()
            self.tipping._right_now = right_now  # pylint: disable=protected-access

            with self.subTest("with no existing match records in DB"):
                self.assertEqual(Match.objects.count(), 0)

                self.tipping.update_match_predictions()

                # It doesn't fetch predictions
                self.tipping.data_importer.fetch_prediction_data.assert_not_called()
                # It doesn't create prediction records
                self.assertEqual(Prediction.objects.count(), 0)

            with self.subTest("with upcoming match records saved in the DB"):
                for fixture_datum in self.fixture_return_values[0].to_dict("records"):
                    match = Match.get_or_create_from_raw_data(fixture_datum)
                    TeamMatch.get_or_create_from_raw_data(match, fixture_datum)

                self.tipping.update_match_predictions()

                # It fetches predictions
                self.tipping.data_importer.fetch_prediction_data.assert_called()
                # It creates prediction records
                self.assertEqual(Prediction.objects.count(), ROW_COUNT)

            next_match = (
                Match.objects.filter(start_date_time__gt=right_now)
                .order_by("start_date_time")
                .first()
            )

        with self.subTest("with played matches in the current round"):
            with freeze_time(next_match.start_date_time + timedelta(days=1)):
                right_now = timezone.localtime()
                self.tipping._right_now = right_now  # pylint: disable=protected-access

                next_match = (
                    Match.objects.filter(start_date_time__gt=right_now)
                    .order_by("start_date_time")
                    .first()
                )

                played_matches = Match.objects.filter(
                    start_date_time__lt=right_now, round_number=next_match.round_number
                )
                self.assertGreater(played_matches.count(), 0)

                past_predictions = played_matches.values(
                    "prediction__id", "prediction__updated_at"
                )

                self.tipping.update_match_predictions()

                # It doesn't update predictions for played matches
                for pred in past_predictions:
                    record_updated_at = Prediction.objects.get(
                        id=pred["prediction__id"]
                    ).updated_at

                    self.assertEqual(pred["prediction__updated_at"], record_updated_at)

    def test_submit_tips(self):
        for _ in range(ROW_COUNT):
            FullMatchFactory(future=True)

        mock_submitter = FootyTipsSubmitter(browser=None)
        mock_submitter.submit_tips = MagicMock()

        with self.subTest("when there are no predictions to submit"):
            self.tipping.submit_tips(tip_submitters=[mock_submitter])

            # It doesn't try to submit any tips
            mock_submitter.submit_tips.assert_not_called()

        ml_model = MLModel.objects.get(is_principal=True)

        for match in Match.objects.all():
            # Need to use competition models for the predictions to get queried
            PredictionFactory(match=match, ml_model=ml_model)

        self.tipping.submit_tips(tip_submitters=[mock_submitter, mock_submitter])

        # It submits tips to all competitions
        self.assertEqual(mock_submitter.submit_tips.call_count, 2)

    def _build_imported_data_mocks(
        self, tip_date
    ) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        with freeze_time(tip_date):
            tomorrow = timezone.localtime() + timedelta(days=1)
            year = tomorrow.year

            # Mock footywire fixture data
            fixture_data = fake_fixture_data(ROW_COUNT, (year, year + 1))

            prediction_match_data, _ = zip(
                *[
                    (
                        self._build_prediction_and_match_results_data(match_data),
                        self._build_teams(match_data),
                    )
                    for match_data in fixture_data.to_dict("records")
                ]
            )

            prediction_data, match_results_data = zip(*prediction_match_data)

        return (
            fixture_data,
            pd.concat(prediction_data),
            pd.DataFrame(list(match_results_data)),
        )

    def _build_prediction_and_match_results_data(self, match_data):
        match_predictions = fake_prediction_data(
            match_data=match_data, ml_model_name=self.ml_model.name
        )

        return (
            match_predictions,
            self._build_match_results_data(match_data, match_predictions),
        )

    @staticmethod
    def _build_match_results_data(match_data, match_predictions):
        home_team_prediction = (
            match_predictions.query("at_home == 1").iloc[0, :].to_dict()
        )
        away_team_prediction = (
            match_predictions.query("at_home == 0").iloc[0, :].to_dict()
        )

        # Making all predictions correct, because trying to get fancy with it
        # resulted in flakiness that was difficult to fix
        return {
            "year": match_data["year"],
            "round_number": match_data["round_number"],
            "home_team": match_data["home_team"],
            "away_team": match_data["away_team"],
            "home_score": home_team_prediction["predicted_margin"] + 50,
            "away_score": away_team_prediction["predicted_margin"] + 50,
        }

    @staticmethod
    def _build_teams(match_data):
        TeamFactory(name=match_data["home_team"])
        TeamFactory(name=match_data["away_team"])
