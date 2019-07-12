from unittest import TestCase
from unittest.mock import Mock, patch

from machine_learning.ml_data import BettingMLData
from machine_learning.data_import import FootywireDataImporter, FitzroyDataImporter
from machine_learning import api
from machine_learning import settings
from tests.fixtures.data_factories import (
    fake_footywire_betting_data,
    fake_fixture_data,
    fake_raw_match_results_data,
)


YEAR_RANGE = (2019, 2020)
N_MATCHES = 5
FAKE_ML_MODELS = [
    {"name": "fake_estimator", "filepath": "src/tests/fixtures/fake_estimator.pkl"}
]


class TestApi(TestCase):
    @patch("machine_learning.api.ML_MODELS", FAKE_ML_MODELS)
    def test_make_predictions(self):
        data_importer = FootywireDataImporter()
        data_importer.get_betting_odds = Mock(
            return_value=fake_footywire_betting_data(N_MATCHES, YEAR_RANGE)
        )

        betting_data = BettingMLData(
            data_readers={"betting": (data_importer.get_betting_odds, {})}
        )

        response = api.make_predictions(
            YEAR_RANGE, 1, data=betting_data, ml_model_names="fake_estimator", verbose=0
        )

        predictions = response["data"]
        # Two predictions per match per model: one for each team playing
        self.assertEqual(len(predictions), N_MATCHES * 2)

        first_prediction = predictions[0]

        self.assertEqual(
            set(first_prediction.keys()),
            set(
                [
                    "team",
                    "year",
                    "round_number",
                    "at_home",
                    "oppo_team",
                    "ml_model",
                    "predicted_margin",
                ]
            ),
        )

        prediction_years = list({pred["year"] for pred in predictions})
        self.assertEqual(prediction_years, [YEAR_RANGE[0]])

    def test_fetch_fixture_data(self):
        data_importer = FitzroyDataImporter()
        data_importer.fetch_fixtures = Mock(
            return_value=fake_fixture_data(N_MATCHES, YEAR_RANGE)
        )

        response = api.fetch_fixture_data(
            "2019-01-01", "2019-12-31", data_import=data_importer, verbose=0
        )

        matches = response["data"]

        self.assertEqual(len(matches), N_MATCHES)

        first_match = matches[0]

        self.assertEqual(
            set(first_match.keys()),
            set(
                [
                    "date",
                    "home_team",
                    "year",
                    "round_number",
                    "away_team",
                    "round_type",
                    "venue",
                ]
            ),
        )

        fixture_years = list({match["year"] for match in matches})
        self.assertEqual(fixture_years, [YEAR_RANGE[0]])

    def test_fetch_match_results_data(self):
        data_importer = FitzroyDataImporter()
        data_importer.match_results = Mock(
            return_value=fake_raw_match_results_data(N_MATCHES, YEAR_RANGE)
        )

        response = api.fetch_match_results_data(
            "2019-01-01", "2019-12-31", data_import=data_importer, verbose=0
        )

        matches = response["data"]

        self.assertEqual(len(matches), N_MATCHES)

        first_match = matches[0]

        self.assertEqual(
            set(first_match.keys()),
            set(
                [
                    "date",
                    "year",
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
        )

        match_years = list({match["year"] for match in matches})
        self.assertEqual(match_years, [YEAR_RANGE[0]])

    def test_fetch_ml_model_info(self):
        response = api.fetch_ml_model_info()

        models = response["data"]

        self.assertEqual(models, settings.ML_MODELS)
