# pylint: disable=missing-docstring
from typing import Tuple
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock

from django.test import TestCase
from django.utils import timezone
from freezegun import freeze_time
import pandas as pd
import numpy as np
from faker import Faker

from data.tipping import Tipper, FootyTipsSubmitter
from server.models import Match, TeamMatch
from server.tests.fixtures.data_factories import fake_fixture_data, fake_prediction_data


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

    @patch("server.api.update_fixture_data")
    def test_fetch_upcoming_fixture(self, mock_api_update_fixture_data):
        with freeze_time(TIP_DATES[0]):
            right_now = timezone.localtime()
            self.tipping._right_now = right_now  # pylint: disable=protected-access

            self.assertEqual(Match.objects.count(), 0)
            self.assertEqual(TeamMatch.objects.count(), 0)

            self.tipping.fetch_upcoming_fixture()

            # It passes fixture data to server.api
            future_fixture_data = self.fixture_return_values[0].query(
                "date > @right_now"
            )
            min_future_round = future_fixture_data["round_number"].min()
            mock_api_update_fixture_data.assert_called_with(
                future_fixture_data.to_dict("records"), min_future_round
            )

        with freeze_time(TIP_DATES[2]):
            mock_api_update_fixture_data.reset_mock()

            with self.subTest("with no future matches"):
                right_now = timezone.localtime()
                self.tipping._right_now = right_now  # pylint: disable=protected-access

                self.tipping.fetch_upcoming_fixture()

                mock_api_update_fixture_data.assert_not_called()

    @patch("data.tipping.tipping.api")
    def test_update_match_predictions(self, mock_api):
        mock_api.update_future_match_predictions = MagicMock()

        with self.subTest("with no future match records available"):
            mock_api.fetch_next_match = MagicMock(return_value=None)

            self.tipping.update_match_predictions()

            # It doesn't fetch predictions
            self.tipping.data_importer.fetch_prediction_data.assert_not_called()
            # It doesn't send predictions to server API
            mock_api.update_future_match_predictions.assert_not_called()

        with self.subTest("with at least one future match record"):
            next_match = (
                self.fixture_return_values[0]
                .sort_values("date", ascending=True)
                .iloc[0]
            )

            mock_api.fetch_next_match = MagicMock(
                return_value={
                    "round_number": next_match["round_number"],
                    "season": next_match["date"].year,
                }
            )

            self.tipping.update_match_predictions()

            # It fetches predictions
            self.tipping.data_importer.fetch_prediction_data.assert_called()
            # It sends predictions to server API
            mock_api.update_future_match_predictions.assert_called()

    @patch("server.api.fetch_latest_round_predictions")
    def test_submit_tips(self, mock_fetch_latest_round_predictions):
        mock_submitter = FootyTipsSubmitter(browser=None)
        mock_submitter.submit_tips = MagicMock()

        with self.subTest("when there are no predictions to submit"):
            mock_fetch_latest_round_predictions.return_value = []

            self.tipping.submit_tips(tip_submitters=[mock_submitter])

            # It doesn't try to submit any tips
            mock_submitter.submit_tips.assert_not_called()

        fake_prediction_values = [
            {
                "predicted_winner__name": FAKE.company(),
                "predicted_margin": FAKE.pyint(min_value=0, max_value=50),
                "predicted_win_probability": np.random.uniform(0.5, 0.99),
            }
            for _ in range(ROW_COUNT)
        ]

        mock_fetch_latest_round_predictions.return_value = fake_prediction_values

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

            prediction_match_data = [
                (self._build_prediction_and_match_results_data(match_data))
                for match_data in fixture_data.to_dict("records")
            ]

            prediction_data, match_results_data = zip(*prediction_match_data)

        return (
            fixture_data,
            pd.concat(prediction_data),
            pd.DataFrame(list(match_results_data)),
        )

    def _build_prediction_and_match_results_data(self, match_data):
        match_predictions = fake_prediction_data(match_data=match_data)

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
