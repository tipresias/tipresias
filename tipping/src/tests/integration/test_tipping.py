# pylint: disable=missing-docstring

from datetime import datetime
from unittest import TestCase
from unittest.mock import Mock, patch, MagicMock
import pytz

from freezegun import freeze_time
import pandas as pd
from requests import Response
from candystore import CandyStore

from tests.fixtures import data_factories
from tipping.tipping import Tipper, FootyTipsSubmitter, MonashSubmitter


MATCH_SEASON_RANGE = (2016, 2018)
# We have 2 subtests in 2016 and 1 in 2017, which requires 3 fixture
# and prediction data imports, but only 1 match results data import,
# because it doesn't get called until 2017
MOCK_IMPORT_SEASONS = [min(MATCH_SEASON_RANGE), *range(*MATCH_SEASON_RANGE)]
TIP_SEASON_RANGE = (min(MATCH_SEASON_RANGE), max(MATCH_SEASON_RANGE) + 1)
TIP_DATES = [
    datetime(season, 1, 1, tzinfo=pytz.UTC)
    for season in range(*TIP_SEASON_RANGE)
]


class TestTipper(TestCase):
    @patch("tipping.data_import")
    def setUp(self, mock_data_import):  # pylint: disable=arguments-differ
        candy = CandyStore(seasons=MATCH_SEASON_RANGE)
        fixtures = pd.DataFrame(
            data_factories.fake_fixture_data(fixtures=candy.fixtures(to_dict=None))
        )
        predictions = data_factories.fake_prediction_data(
            fixtures=candy.fixtures(to_dict=None)
        )
        match_results = data_factories.fake_match_data(
            match_results=candy.match_results(to_dict=None)
        )

        season_fixtures = [
            fixtures.query('year == @season')
            for season in MOCK_IMPORT_SEASONS
        ]
        self.first_season_fixture = season_fixtures[0]
        season_predictions = [
            predictions.query('year == @season')
            for season in MOCK_IMPORT_SEASONS
        ]
        season_match_results = match_results.query('year == @TIP_SEASON_RANGE[0]')

        mock_data_import.fetch_prediction_data = Mock(
            side_effect=season_predictions
        )
        mock_data_import.fetch_fixture_data = Mock(
            side_effect=season_fixtures
        )
        mock_data_import.fetch_match_data = Mock(
            return_value=season_match_results
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
            fixture_data = self.first_season_fixture
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
                return_value=self.first_season_fixture
            )

            self.tipping.update_match_predictions()

            # It fetches predictions
            self.tipping.data_importer.fetch_prediction_data.assert_called()
            # It sends predictions to Tipresias app
            mock_data_export.update_match_predictions.assert_called()
            # It submits tips to all competitions
            self.mock_footy_tips_submitter._call_splash_service.assert_called()  # pylint: disable=protected-access
            self.mock_monash_submitter._submit_competition_tips.assert_called()  # pylint: disable=protected-access
