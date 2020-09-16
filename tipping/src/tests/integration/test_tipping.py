# pylint: disable=missing-docstring

from typing import Tuple
from datetime import datetime, timedelta
from unittest import TestCase
from unittest.mock import Mock, patch, MagicMock
import pytz

from freezegun import freeze_time
import pandas as pd
from faker import Faker
from requests import Response

from tests.fixtures import data_factories
from tipping.tipping import Tipper, FootyTipsSubmitter, MonashSubmitter


ROW_COUNT = 5
TIP_DATES = [
    datetime(2016, 1, 1, tzinfo=pytz.UTC),
    datetime(2017, 1, 1, tzinfo=pytz.UTC),
    datetime(2018, 1, 1, tzinfo=pytz.UTC),
]
FAKE = Faker()


class TestTipper(TestCase):
    @patch("tipping.data_import")
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
        mock_data_import.fetch_match_data = Mock(
            return_value=match_results_return_values[0]
        )

        self.mock_footy_tips_submitter = FootyTipsSubmitter(browser=None)
        mock_response = Response()
        mock_response.status_code = 200
        self.mock_footy_tips_submitter._call_splash_service = MagicMock(  # pylint: disable=protected-access
            return_value=mock_response
        )

        self.mock_monash_submitter = MonashSubmitter(browser=None)
        self.mock_monash_submitter._submit_competition_tips = (  # pylint: disable=protected-access
            MagicMock()
        )

        self.tipping = Tipper(
            data_importer=mock_data_import,
            tip_submitters=[self.mock_footy_tips_submitter, self.mock_monash_submitter],
            verbose=0,
        )

    @patch("tipping.data_export.update_fixture_data")
    def test_fetch_upcoming_fixture(self, mock_update_fixture_data):
        with freeze_time(TIP_DATES[0]):
            right_now = datetime.now(tz=pytz.UTC)
            self.tipping._right_now = right_now  # pylint: disable=protected-access

            self.tipping.fetch_upcoming_fixture()

            # It passes fixture data to data_export
            fixture_data = self.fixture_return_values[0]
            future_fixture_data = fixture_data.query("date > @right_now")
            min_future_round = future_fixture_data["round_number"].min()
            # Have to get creative with checking args because we can't compare
            # data frames with a simple equality check
            mock_update_fixture_data.assert_called_once()

            fixture_arg = mock_update_fixture_data.mock_calls[0].args[0]
            expected_fixture_arg = fixture_data.query(
                'round_number == @min_future_round'
            )
            self.assertTrue(
                (fixture_arg == expected_fixture_arg)
                .all()
                .all()
            )

            round_number_arg = mock_update_fixture_data.mock_calls[0].args[1]
            self.assertEqual(
                round_number_arg, min_future_round
            )

        with freeze_time(TIP_DATES[2]):
            mock_update_fixture_data.reset_mock()

            with self.subTest("with no future matches"):
                right_now = datetime.now(tz=pytz.UTC)
                self.tipping._right_now = right_now  # pylint: disable=protected-access

                self.tipping.fetch_upcoming_fixture()

                mock_update_fixture_data.assert_not_called()

    @patch("tipping.tipping.data_export")
    @patch("tipping.tipping.data_import")
    def test_update_match_predictions(self, mock_data_import, mock_data_export):
        mock_data_export.update_match_predictions = MagicMock()

        with self.subTest("with no future match records available"):
            mock_data_import.fetch_fixture_data = MagicMock(return_value=pd.DataFrame())

            self.tipping.update_match_predictions()

            # It doesn't fetch predictions
            self.tipping.data_importer.fetch_prediction_data.assert_not_called()
            # It doesn't send predictions to server API
            mock_data_export.update_match_predictions.assert_not_called()
            # It doesn't try to submit any tips
            self.mock_footy_tips_submitter._call_splash_service.assert_not_called()  # pylint: disable=protected-access
            self.mock_monash_submitter._submit_competition_tips.assert_not_called()  # pylint: disable=protected-access

        with self.subTest("with at least one future match record"):
            mock_data_import.fetch_fixture_data = MagicMock(
                return_value=self.fixture_return_values[0]
            )

            self.tipping.update_match_predictions()

            # It fetches predictions
            self.tipping.data_importer.fetch_prediction_data.assert_called()
            # It sends predictions to Tipresias app
            mock_data_export.update_match_predictions.assert_called()
            # It submits tips to all competitions
            self.mock_footy_tips_submitter._call_splash_service.assert_called()  # pylint: disable=protected-access
            self.mock_monash_submitter._submit_competition_tips.assert_called()  # pylint: disable=protected-access

    def _build_imported_data_mocks(
        self, tip_date
    ) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        with freeze_time(tip_date):
            tomorrow = datetime.now(tz=pytz.UTC) + timedelta(days=1)
            year = tomorrow.year

            # Mock footywire fixture data
            fixture_data = data_factories.fake_fixture_data((year, year + 1))

            prediction_match_data = [
                (self._build_prediction_and_match_results_data(match_data))
                for match_data in fixture_data
            ]

            prediction_data, match_results_data = zip(*prediction_match_data)

        return (
            pd.DataFrame(fixture_data),
            pd.concat(prediction_data),
            pd.DataFrame(list(match_results_data)),
        )

    def _build_prediction_and_match_results_data(self, match_data):
        match_predictions = data_factories.fake_prediction_data(match_data=match_data)

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
