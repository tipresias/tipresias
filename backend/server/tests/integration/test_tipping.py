# pylint: disable=missing-docstring
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

from django.test import TestCase
from django.utils import timezone
from freezegun import freeze_time
import pandas as pd

from server.models import Match, TeamMatch, Prediction
from server.tipping import Tipper
from server.tests.fixtures.data_factories import fake_fixture_data, fake_prediction_data
from server.tests.fixtures.factories import MLModelFactory, TeamFactory


ROW_COUNT = 5
TIP_DATES = [
    timezone.make_aware(datetime(2016, 1, 1)),
    timezone.make_aware(datetime(2017, 1, 1)),
]


class TestTipper(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        MLModelFactory(name="test_estimator")

    @patch("server.data_import")
    def setUp(self, mock_data_import):  # pylint: disable=arguments-differ
        (
            fixture_return_values,
            prediction_return_values,
            match_results_return_values,
        ) = zip(*[self.__build_imported_data_mocks(tip_date) for tip_date in TIP_DATES])

        # We have 2 subtests in 2016 and 1 in 2017, which requires 3 fixture
        # and prediction data imports, but only 1 match results data import,
        # because it doesn't get called until 2017
        mock_data_import.fetch_prediction_data = Mock(
            side_effect=prediction_return_values[:1] + prediction_return_values
        )
        mock_data_import.fetch_fixture_data = Mock(
            side_effect=fixture_return_values[:1] + fixture_return_values
        )
        mock_data_import.fetch_match_results_data = Mock(
            return_value=match_results_return_values[0]
        )

        # Not fetching data, because it takes forever
        self.tipping = Tipper(
            fetch_data=False, data_importer=mock_data_import, tip_submitters=[]
        )

    def test_tip(self):
        with freeze_time(TIP_DATES[0]):
            right_now = timezone.localtime()
            self.tipping._right_now = right_now  # pylint: disable=protected-access

            with self.subTest("with no existing match records in DB"):
                self.assertEqual(Match.objects.count(), 0)
                self.assertEqual(TeamMatch.objects.count(), 0)

                self.tipping.tip(verbose=0)

                self.assertEqual(Match.objects.count(), ROW_COUNT)
                self.assertEqual(TeamMatch.objects.count(), ROW_COUNT * 2)

            with self.subTest("with the match records already saved in the DB"):
                self.assertEqual(Match.objects.count(), ROW_COUNT)
                self.assertEqual(TeamMatch.objects.count(), ROW_COUNT * 2)

                self.tipping.tip(verbose=0)

                self.assertEqual(Match.objects.count(), ROW_COUNT)
                self.assertEqual(TeamMatch.objects.count(), ROW_COUNT * 2)

        with freeze_time(TIP_DATES[1]):
            with self.subTest("with scoreless matches from ealier rounds"):
                right_now = timezone.localtime()
                self.tipping._right_now = right_now  # pylint: disable=protected-access

                self.assertEqual(TeamMatch.objects.filter(score__gt=0).count(), 0)
                self.assertEqual(Prediction.objects.filter(is_correct=True).count(), 0)

                self.tipping.tip(verbose=0)

                self.assertEqual(
                    TeamMatch.objects.filter(
                        match__start_date_time__lt=right_now, score=0
                    ).count(),
                    0,
                )

    def __build_imported_data_mocks(self, tip_date):
        with freeze_time(tip_date):
            tomorrow = timezone.localtime() + timedelta(days=1)
            year = tomorrow.year

            # Mock footywire fixture data
            fixture_data = fake_fixture_data(ROW_COUNT, (year, year + 1))

            prediction_match_data, _ = zip(
                *[
                    (
                        self.__build_prediction_and_match_results_data(match_data),
                        self.__build_teams(match_data),
                    )
                    for match_data in fixture_data.to_dict("records")
                ]
            )

            prediction_data, match_results_data = zip(*prediction_match_data)

        return (
            fixture_data,
            pd.concat(prediction_data),
            pd.DataFrame(list(match_results_data)),
        )

    def __build_prediction_and_match_results_data(self, match_data):
        match_predictions = fake_prediction_data(
            match_data=match_data, ml_model_name="test_estimator"
        )

        return (
            match_predictions,
            self.__build_match_results_data(match_data, match_predictions),
        )

    @staticmethod
    def __build_match_results_data(match_data, match_predictions):
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

    @staticmethod
    def __build_teams(match_data):
        TeamFactory(name=match_data["home_team"])
        TeamFactory(name=match_data["away_team"])
