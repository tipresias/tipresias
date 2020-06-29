# pylint: disable=missing-docstring

from unittest import TestCase
from unittest.mock import patch, MagicMock

import pandas as pd
import numpy as np

from tests.fixtures import data_factories
from tipping import api


N_MATCHES = 5
YEAR_RANGE = (2016, 2017)


class TestApi(TestCase):
    def setUp(self):
        self.api = api

    @patch("tipping.api.data_import")
    def test_fetch_match_predictions(self, mock_data_import):
        matches = data_factories.fake_match_results_data(N_MATCHES, YEAR_RANGE)
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
            set(
                [
                    "home_team",
                    "year",
                    "round_number",
                    "away_team",
                    "ml_model",
                    "home_predicted_margin",
                    "away_predicted_margin",
                    "home_predicted_win_probability",
                    "away_predicted_win_probability",
                ]
            ),
            set(prediction_response[0].keys()),
        )
        self.assertEqual(N_MATCHES, len(prediction_response))

    @patch("tipping.api.data_import")
    def test_fetch_match_results(self, mock_data_import):
        matches = data_factories.fake_match_results_data(N_MATCHES, YEAR_RANGE)
        mock_data_import.fetch_match_results_data = MagicMock(return_value=matches)

        match_dates = np.random.choice(matches["date"], size=2)
        fetch_data = bool(np.random.randint(0, 2))

        match_response = self.api.fetch_match_results(
            start_date=min(match_dates),
            end_date=max(match_dates),
            fetch_data=fetch_data,
        )

        # It calls fetch_match_results_data with the same params
        mock_data_import.fetch_match_results_data.assert_called_with(
            min(match_dates), max(match_dates), fetch_data=fetch_data,
        )
        # It returns match data
        self.assertEqual(
            set(
                [
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
                ]
            ),
            set(match_response[0].keys()),
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
            set(["name", "prediction_type", "trained_to", "data_set", "label_col",]),
            set(ml_model_response[0].keys()),
        )
        self.assertEqual(N_ML_MODELS, len(ml_model_response))
