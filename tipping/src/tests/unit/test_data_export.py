# pylint: disable=missing-docstring

from unittest import TestCase
from unittest.mock import patch, MagicMock
import json

import numpy as np
import pandas as pd

from tests.fixtures import data_factories
from tipping import data_export, settings


N_MATCHES = 5
YEAR_RANGE = (2016, 2017)


class TestDataExport(TestCase):
    def setUp(self):
        self.data_export = data_export

    @patch("tipping.data_export.requests")
    def test_update_fixture_data(self, mock_requests):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {}
        mock_response.text = "Stuff happened"

        mock_requests.post = MagicMock(return_value=mock_response)

        url = settings.TIPRESIAS_APP + "/fixtures"
        fake_fixture = data_factories.fake_fixture_data(N_MATCHES, YEAR_RANGE)
        upcoming_round = np.random.randint(1, 24)
        self.data_export.update_fixture_data(fake_fixture, upcoming_round)

        # It posts the data
        fixture_response = fake_fixture.astype({"date": str}).to_dict("records")
        mock_requests.post.assert_called_with(
            url,
            json={"upcoming_round": upcoming_round, "data": fixture_response},
            headers={},
        )

        with self.subTest("when the status code isn't 2xx"):
            mock_response.status_code = 400

            with self.assertRaisesRegex(Exception, "Bad response"):
                self.data_export.update_fixture_data(fake_fixture, upcoming_round)

    @patch("tipping.data_export.requests")
    def test_update_match_predictions(self, mock_requests):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {}
        response_data = [
            {
                "predicted_winner__name": "Some Team",
                # Can't use 'None' for either prediction value, because it messes
                # with pandas equality checks
                "predicted_margin": 5.23,
                "predicted_win_probability": 0.876,
            }
        ]
        mock_response.text = json.dumps(response_data)

        mock_requests.post = MagicMock(return_value=mock_response)

        url = settings.TIPRESIAS_APP + "/predictions"
        fake_predictions = pd.concat(
            [data_factories.fake_prediction_data() for _ in range(N_MATCHES)]
        )
        prediction_records = self.data_export.update_match_predictions(fake_predictions)

        # It posts the data
        prediction_data = fake_predictions.to_dict("records")
        mock_requests.post.assert_called_with(
            url, json={"data": prediction_data}, headers={}
        )

        # It returns the created/updated predictions records
        self.assertTrue((prediction_records == pd.DataFrame(response_data)).all().all())

        with self.subTest("when the status code isn't 2xx"):
            mock_response.status_code = 400

            with self.assertRaisesRegex(Exception, "Bad response"):
                self.data_export.update_match_predictions(fake_predictions)

    @patch("tipping.data_export.requests")
    def test_update_matches(self, mock_requests):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {}
        mock_response.text = "Stuff happened"

        mock_requests.post = MagicMock(return_value=mock_response)

        url = settings.TIPRESIAS_APP + "/matches"
        fake_matches = data_factories.fake_match_data(N_MATCHES, YEAR_RANGE)
        self.data_export.update_matches(fake_matches)

        # It posts the data
        matches_response = fake_matches.astype({"date": str}).to_dict("records")
        mock_requests.post.assert_called_with(
            url, json={"data": matches_response}, headers={}
        )

        with self.subTest("when the status code isn't 2xx"):
            mock_response.status_code = 400

            with self.assertRaisesRegex(Exception, "Bad response"):
                self.data_export.update_matches(fake_matches)

    @patch("tipping.data_export.requests")
    def test_update_match_results(self, mock_requests):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {}
        mock_response.text = "Stuff happened"

        mock_requests.post = MagicMock(return_value=mock_response)

        url = settings.TIPRESIAS_APP + "/matches"
        fake_match_results = data_factories.fake_match_results_data(
            N_MATCHES, YEAR_RANGE
        )
        self.data_export.update_match_results(fake_match_results)

        # It posts the data
        match_results_response = fake_match_results.astype({"date": str}).to_dict(
            "records"
        )
        mock_requests.post.assert_called_with(
            url, json={"data": match_results_response}, headers={}
        )

        with self.subTest("when the status code isn't 2xx"):
            mock_response.status_code = 400

            with self.assertRaisesRegex(Exception, "Bad response"):
                self.data_export.update_match_results(fake_match_results)
