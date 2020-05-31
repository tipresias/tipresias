# pylint: disable=missing-docstring

from unittest import skip
from unittest.mock import patch, Mock
from datetime import datetime, timedelta

from django.test import TestCase
from django.utils import timezone
import pandas as pd
from faker import Faker

from server.tests.fixtures import data_factories, factories
from server.management.commands import tip
from server.models import Match, Prediction

ROW_COUNT = 5
TIP_DATES = [
    timezone.make_aware(datetime(2016, 1, 1)),
    timezone.make_aware(datetime(2017, 1, 1)),
]
FAKE = Faker()


class TestTip(TestCase):
    def setUp(self):  # pylint: disable=arguments-differ
        self.tip_command = tip.Command()

    @skip(
        "For some reason, the mock data import isn't working in CI, "
        "so we're getting real data."
    )
    @patch("server.tipping.data_import")
    def test_handle(self, mock_data_import):
        self._stub_import_methods(mock_data_import)

        self.assertEqual(Match.objects.count(), 0)

        self.tip_command.handle(verbose=0)

        # It creates upcoming match records
        self.assertEqual(Match.objects.count(), ROW_COUNT)
        # It requests predictions
        mock_data_import.request_predictions.assert_called()
        self.assertEqual(Prediction.objects.count(), 0)

    def _stub_import_methods(self, mock_data_import):
        (
            fixture_return_values,
            match_results_return_values,
        ) = self._build_imported_data_mocks()

        # We have 2 subtests in 2016 and 1 in 2017, which requires 3 fixture
        # and prediction data imports, but only 1 match results data import,
        # because it doesn't get called until 2017
        mock_data_import.request_predictions = Mock(
            side_effect=self._request_predictions
        )
        mock_data_import.fetch_fixture_data = Mock(return_value=fixture_return_values)
        mock_data_import.fetch_match_results_data = Mock(
            return_value=match_results_return_values
        )

    def _build_imported_data_mocks(self):
        tomorrow = timezone.localtime() + timedelta(days=1)
        year = tomorrow.year

        # Mock footywire fixture data
        fixture_data = data_factories.fake_fixture_data(ROW_COUNT, (year, year + 1))

        match_results_data, _ = zip(
            *[
                (
                    self._build_match_results_data(match_data),
                    self._build_teams(match_data),
                )
                for match_data in fixture_data.to_dict("records")
            ]
        )

        return (
            fixture_data,
            pd.DataFrame(list(match_results_data)),
        )

    @staticmethod
    def _build_match_results_data(match_data):
        # Making all predictions correct, because trying to get fancy with it
        # resulted in flakiness that was difficult to fix
        return {
            "year": match_data["year"],
            "round_number": match_data["round_number"],
            "home_team": match_data["home_team"],
            "away_team": match_data["away_team"],
            "home_score": FAKE.pyint(min_value=0, max_value=200),
            "away_score": FAKE.pyint(min_value=0, max_value=200),
        }

    @staticmethod
    def _build_teams(match_data):
        factories.TeamFactory(name=match_data["home_team"])
        factories.TeamFactory(name=match_data["away_team"])

    @staticmethod
    def _request_predictions(
        year_range,
        round_number=None,
        ml_models=None,
        train_models=False,  # pylint: disable=unused-argument
    ):
        return {
            "ml_models": ml_models,
            "round_number": round_number,
            "year_range": list(year_range),
        }
