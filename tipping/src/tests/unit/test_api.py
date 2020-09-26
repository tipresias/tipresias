# pylint: disable=missing-docstring

from unittest import TestCase
from unittest.mock import patch, MagicMock
from datetime import datetime, date
import pytz

import numpy as np
from freezegun import freeze_time
from candystore import CandyStore

from tests.fixtures import data_factories
from tipping import api
from tipping.tipping import FootyTipsSubmitter


TODAY = date.today()
CURRENT_YEAR = TODAY.year
CURRENT_YEAR_RANGE = (CURRENT_YEAR, CURRENT_YEAR + 1)

MATCH_SEASON_RANGE = (2016, 2018)
# We have 2 subtests in 2016 and 1 in 2017, which requires 3 fixture
# and prediction data imports, but only 1 match results data import,
# because it doesn't get called until 2017
MOCK_IMPORT_SEASONS = [min(MATCH_SEASON_RANGE), *range(*MATCH_SEASON_RANGE)]
TIP_SEASON_RANGE = (min(MATCH_SEASON_RANGE), max(MATCH_SEASON_RANGE) + 1)
TIP_DATES = [
    datetime(season, 1, 1, tzinfo=pytz.UTC) for season in range(*TIP_SEASON_RANGE)
]


class TestApi(TestCase):
    def setUp(self):
        candy = CandyStore(seasons=MATCH_SEASON_RANGE)
        fixtures = data_factories.fake_fixture_data(
            fixtures=candy.fixtures(to_dict=None)
        )
        predictions = data_factories.fake_prediction_data(
            fixtures=candy.fixtures(to_dict=None)
        )

        self.fixture_return_values = [
            fixtures.query("year == @season") for season in MOCK_IMPORT_SEASONS
        ]
        # self.first_season_fixture = season_fixtures[0]
        self.prediction_return_values = [
            predictions.query("year == @season") for season in MOCK_IMPORT_SEASONS
        ]

        self.mock_submitter = FootyTipsSubmitter()
        self.mock_submitter.submit_tips = MagicMock()

        self.api = api

    @patch("tipping.api.data_export")
    @patch("tipping.api.data_import")
    def test_update_fixture_data(self, mock_data_import, mock_data_export):
        with freeze_time(datetime(2020, 5, 1, tzinfo=pytz.UTC)):
            right_now = datetime.now(tz=pytz.UTC)
            this_year = right_now.year
            fixture = data_factories.fake_fixture_data(
                seasons=(this_year, this_year + 1)
            )
            upcoming_round = int(
                fixture.query("date > @right_now")["round_number"].min()
            )

            mock_data_import.fetch_fixture_data = MagicMock(return_value=fixture)
            mock_data_export.update_fixture_data = MagicMock()

            self.api.update_fixture_data()

            # It posts data to main app
            mock_data_export.update_fixture_data.assert_called()
            call_args = mock_data_export.update_fixture_data.call_args[0]

            data_are_equal = (
                (call_args[0] == fixture.query("round_number == @upcoming_round"))
                .all()
                .all()
            )
            self.assertTrue(data_are_equal)
            self.assertEqual(call_args[1], upcoming_round)

    @patch("tipping.api.data_export")
    @patch("tipping.api.data_import")
    def test_update_matches(self, mock_data_import, mock_data_export):
        matches = data_factories.fake_match_data()

        mock_data_import.fetch_match_data = MagicMock(return_value=matches)
        mock_data_export.update_matches = MagicMock()

        self.api.update_matches(verbose=0)

        # It posts data to main app
        mock_data_export.update_matches.assert_called()
        call_args = mock_data_export.update_matches.call_args[0]
        data_are_equal = (call_args[0] == matches).all().all()
        self.assertTrue(data_are_equal)

    @patch("tipping.api.data_export")
    @patch("tipping.api.data_import")
    def test_update_match_predictions(self, mock_data_import, mock_data_export):
        mock_data_export.update_match_predictions = MagicMock()
        mock_data_import.fetch_prediction_data = MagicMock(
            side_effect=self.prediction_return_values
        )
        mock_data_import.fetch_fixture_data = MagicMock(
            side_effect=self.fixture_return_values
        )

        mock_submitter = FootyTipsSubmitter(verbose=0)
        mock_submitter.submit_tips = MagicMock()

        with self.subTest("with no future match records available"):
            self.api.update_match_predictions(
                tips_submitters=[mock_submitter, mock_submitter], verbose=0
            )

            # It doesn't fetch predictions
            mock_data_import.fetch_prediction_data.assert_not_called()
            # It doesn't send predictions to server API
            mock_data_export.update_match_predictions.assert_not_called()
            # It doesn't try to submit any tips
            mock_submitter.submit_tips.assert_not_called()

        with self.subTest("with at least one future match record"):
            with freeze_time(TIP_DATES[0]):
                self.api.update_match_predictions(
                    tips_submitters=[mock_submitter, mock_submitter], verbose=0
                )

                # It fetches predictions
                mock_data_import.fetch_prediction_data.assert_called()
                # It sends predictions to Tipresias app
                mock_data_export.update_match_predictions.assert_called()
                # It submits tips to all competitions
                self.assertEqual(mock_submitter.submit_tips.call_count, 2)

    @patch("tipping.api.data_import")
    def test_fetch_match_predictions(self, mock_data_import):
        fixtures = data_factories.fake_fixture_data(seasons=CURRENT_YEAR_RANGE)
        predictions = data_factories.fake_prediction_data(fixtures=fixtures)
        mock_data_import.fetch_prediction_data = MagicMock(return_value=predictions)

        round_number = np.random.choice(fixtures["round_number"])
        ml_models = list(set(np.random.choice(predictions["ml_model"], 2)))
        train_models = bool(np.random.randint(0, 2))

        prediction_response = self.api.fetch_match_predictions(
            CURRENT_YEAR_RANGE,
            round_number=round_number,
            ml_models=ml_models,
            train_models=train_models,
        )

        # It calls fetch_prediction_data with the same params
        mock_data_import.fetch_prediction_data.assert_called_with(
            CURRENT_YEAR_RANGE,
            round_number=round_number,
            ml_models=ml_models,
            train_models=train_models,
        )
        # It returns predictions organised by match
        self.assertEqual(
            {
                "home_team",
                "year",
                "round_number",
                "away_team",
                "ml_model",
                "home_predicted_margin",
                "away_predicted_margin",
                "home_predicted_win_probability",
                "away_predicted_win_probability",
            },
            set(prediction_response.columns),
        )
        self.assertEqual(len(fixtures), len(prediction_response))

    @patch("tipping.api.data_import")
    def test_fetch_matches(self, mock_data_import):
        matches = data_factories.fake_match_data()
        mock_data_import.fetch_match_data = MagicMock(return_value=matches)

        match_dates = np.random.choice(matches["date"], size=2)
        fetch_data = bool(np.random.randint(0, 2))

        match_response = self.api.fetch_matches(
            start_date=min(match_dates),
            end_date=max(match_dates),
            fetch_data=fetch_data,
        )

        # It calls fetch_match_data with the same params
        mock_data_import.fetch_match_data.assert_called_with(
            min(match_dates),
            max(match_dates),
            fetch_data=fetch_data,
        )

        match_columns = set(match_response.columns)
        required_columns = {
            "date",
            "year",
            "round",
            "round_number",
            "home_team",
            "away_team",
            "venue",
            "home_score",
            "away_score",
        }
        # It returns match data
        self.assertEqual(
            match_columns & required_columns,
            required_columns,
        )
        self.assertEqual(len(matches), len(match_response))

    @patch("tipping.api.data_import")
    def test_fetch_ml_models(self, mock_data_import):
        N_ML_MODELS = 2
        ml_models = data_factories.fake_ml_model_data(N_ML_MODELS)
        mock_data_import.fetch_ml_model_info = MagicMock(return_value=ml_models)

        ml_model_response = self.api.fetch_ml_models()

        # It calls fetch_ml_model_info
        mock_data_import.fetch_ml_model_info.assert_called()
        # It returns ML model data
        self.assertEqual(
            {"name", "prediction_type", "trained_to", "data_set", "label_col"},
            set(ml_model_response.columns),
        )
        self.assertEqual(N_ML_MODELS, len(ml_model_response))
