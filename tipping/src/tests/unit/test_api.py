# pylint: disable=missing-docstring

from typing import Tuple
from unittest import TestCase
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta
import pytz

import pandas as pd
import numpy as np
from freezegun import freeze_time

from tests.fixtures import data_factories
from tipping import api
from tipping.tipping import FootyTipsSubmitter


N_MATCHES = 5
YEAR_RANGE = (2016, 2017)

TIP_DATES = [
    datetime(2016, 1, 1, tzinfo=pytz.UTC),
    datetime(2017, 1, 1, tzinfo=pytz.UTC),
    datetime(2018, 1, 1, tzinfo=pytz.UTC),
]


class TestApi(TestCase):
    def setUp(self):
        (
            self.fixture_return_values,
            self.prediction_return_values,
            _match_results_return_values,
        ) = zip(
            *[self._build_imported_data_mocks(tip_date) for tip_date in TIP_DATES[:2]]
        )

        self.mock_submitter = FootyTipsSubmitter()
        self.mock_submitter.submit_tips = MagicMock()

        self.api = api

    @patch("tipping.api.data_export")
    @patch("tipping.api.data_import")
    def test_update_fixture_data(self, mock_data_import, mock_data_export):
        this_year = datetime.now().year
        fixture = data_factories.fake_fixture_data(
            N_MATCHES, (this_year, this_year + 1)
        )
        upcoming_round = int(fixture["round_number"].min())

        mock_data_import.fetch_fixture_data = MagicMock(return_value=fixture)
        mock_data_export.update_fixture_data = MagicMock()

        self.api.update_fixture_data()

        # It posts data to main app
        mock_data_export.update_fixture_data.assert_called()
        call_args = mock_data_export.update_fixture_data.call_args[0]
        data_are_equal = (call_args[0] == fixture).all().all()
        self.assertTrue(data_are_equal)
        self.assertEqual(call_args[1], upcoming_round)

    @patch("tipping.api.data_export")
    @patch("tipping.api.data_import")
    def test_update_matches(self, mock_data_import, mock_data_export):
        this_year = datetime.now().year
        matches = data_factories.fake_match_data(N_MATCHES, (this_year, this_year + 1))

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
            side_effect=self.prediction_return_values[:1]
            + self.prediction_return_values
        )
        mock_data_import.fetch_fixture_data = MagicMock(
            side_effect=self.fixture_return_values[:1] + self.fixture_return_values
        )

        mock_submitter = FootyTipsSubmitter(verbose=0)
        mock_submitter.submit_tips = MagicMock()

        with self.subTest("with no future match records available"):
            mock_data_import.fetch_fixture_data = MagicMock(return_value=pd.DataFrame())

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
            mock_data_import.fetch_fixture_data = MagicMock(
                return_value=self.fixture_return_values[0]
            )

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
        matches = data_factories.fake_match_data(N_MATCHES, YEAR_RANGE)
        predictions = pd.concat(
            [
                data_factories.fake_prediction_data(match)
                for match in matches.to_dict("records")
            ]
        )
        mock_data_import.fetch_prediction_data = MagicMock(return_value=predictions)

        round_number = np.random.choice(matches["round_number"])
        ml_models = list(set(np.random.choice(predictions["ml_model"], 2)))
        train_models = bool(np.random.randint(0, 2))

        prediction_response = self.api.fetch_match_predictions(
            YEAR_RANGE,
            round_number=round_number,
            ml_models=ml_models,
            train_models=train_models,
        )

        # It calls fetch_prediction_data with the same params
        mock_data_import.fetch_prediction_data.assert_called_with(
            YEAR_RANGE,
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
        self.assertEqual(N_MATCHES, len(prediction_response))

    @patch("tipping.api.data_import")
    def test_fetch_matches(self, mock_data_import):
        matches = data_factories.fake_match_data(N_MATCHES, YEAR_RANGE)
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
            min(match_dates), max(match_dates), fetch_data=fetch_data,
        )
        # It returns match data
        self.assertEqual(
            {
                "date",
                "year",
                "round",
                "round_number",
                "home_team",
                "away_team",
                "venue",
                "home_score",
                "away_score",
                "match_id",
                "crowd",
            },
            set(match_response.columns),
        )
        self.assertEqual(N_MATCHES, len(match_response))

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

    def _build_imported_data_mocks(
        self, tip_date
    ) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        with freeze_time(tip_date):
            tomorrow = datetime.now(tz=pytz.UTC) + timedelta(days=1)
            year = tomorrow.year

            # Mock footywire fixture data
            fixture_data = data_factories.fake_fixture_data(N_MATCHES, (year, year + 1))

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
