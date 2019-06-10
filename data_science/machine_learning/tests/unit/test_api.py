from unittest import TestCase
import os

from machine_learning import api
from machine_learning.ml_data import BettingMLData

ROW_COUNT = 5


class TestApi(TestCase):
    def setUp(self):
        self.data = BettingMLData()
        self.ml_models = [
            {
                "name": "test_estimator",
                "filepath": os.path.join(
                    "machine_learning/tests/fixtures/test_estimator.pkl"
                ),
            }
        ]

    def test_make_predictions(self):
        year = 2015
        round_number = 5

        filtered_data = self.data.data.query(
            "year == @year and round_number == @round_number"
        )
        predictions = api.make_predictions(
            year, round_number, ml_models=self.ml_models, data=self.data
        )

        self.assertIsInstance(predictions, list)
        self.assertEqual(len(predictions), len(filtered_data))

        prediction = predictions[0]
        prediction_fields = set(prediction.keys())

        self.assertEqual(
            prediction_fields,
            set(
                [
                    "team",
                    "year",
                    "round_number",
                    "at_home",
                    "ml_model",
                    "predicted_margin",
                ]
            ),
        )
