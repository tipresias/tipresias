import copy
from datetime import datetime, timedelta
from unittest.mock import Mock, patch
from unittest import skipIf
import os

from django.test import TestCase
from freezegun import freeze_time
import pandas as pd
import numpy as np

from server.models import Match, TeamMatch, Prediction
from server.management.commands import tip
from server.tests.fixtures.data_factories import fake_fixture_data, fake_prediction_data
from server.tests.fixtures.factories import MLModelFactory, TeamFactory
from project.settings.data_config import TEAM_NAMES
from project.settings.common import MELBOURNE_TIMEZONE


ROW_COUNT = 5
TIP_DATES = ["2016-01-01", "2017-01-01"]


class TestTip(TestCase):
    # Freezing time to make sure there is viable data, which is easier
    # than mocking viable data
    @freeze_time("2016-01-01")
    @patch("server.data_import")
    def setUp(self, mock_data_import):  # pylint: disable=arguments-differ
        MLModelFactory(name="test_estimator")

        fixture_return_values = []
        prediction_return_values = []
        match_results_return_values = []

        for tip_date in TIP_DATES:
            with freeze_time(tip_date):
                tomorrow = datetime.now() + timedelta(days=1)
                year = tomorrow.year

                # Mock footywire fixture data
                fixture_data = fake_fixture_data(ROW_COUNT, (year, year + 1))

                # Mock update_or_create_from_data to make assertions on calls
                update_or_create_from_data = copy.copy(
                    Prediction.update_or_create_from_data
                )
                Prediction.update_or_create_from_data = Mock(
                    side_effect=self.__update_or_create_from_data(
                        update_or_create_from_data
                    )
                )

                prediction_data = []
                match_results = []

                for idx, match_data in enumerate(fixture_data.to_dict("records")):
                    TeamFactory(name=match_data["home_team"])
                    TeamFactory(name=match_data["away_team"])

                    match_predictions = fake_prediction_data(
                        match_data=match_data, ml_model_name="test_estimator"
                    )

                    prediction_data.append(match_predictions)
                    home_team_prediction = (
                        match_predictions.query("at_home == 1").iloc[0, :].to_dict()
                    )
                    away_team_prediction = (
                        match_predictions.query("at_home == 0").iloc[0, :].to_dict()
                    )

                    is_correct = idx % 2 == 0

                    home_score = np.random.randint(50, 150)
                    predicted_winner = (
                        home_team_prediction["team"]
                        if home_team_prediction["predicted_margin"]
                        > away_team_prediction["predicted_margin"]
                        else away_team_prediction["team"]
                    )
                    away_score = (
                        home_score + 25
                        if predicted_winner == match_data["away_team"] and is_correct
                        else home_score - 25
                    )

                    match_results.append(
                        {
                            "year": match_data["year"],
                            "round_number": match_data["round_number"],
                            "home_team": match_data["home_team"],
                            "away_team": match_data["away_team"],
                            "home_score": home_score,
                            "away_score": away_score,
                        }
                    )

            # We have 2 subtests in 2016 and 1 in 2017, which requires 3 fixture
            # and prediction data imports, but only 1 match results data import
            if tip_date == TIP_DATES[0]:
                fixture_return_values.extend([fixture_data] * 2)
                prediction_return_values.extend([pd.concat(prediction_data)] * 2)
            else:
                fixture_return_values.append(fixture_data)
                prediction_return_values.append(pd.concat(prediction_data))

            match_results_return_values.append(pd.DataFrame(match_results))

        mock_data_import.fetch_prediction_data = Mock(
            side_effect=prediction_return_values
        )
        mock_data_import.fetch_fixture_data = Mock(side_effect=fixture_return_values)
        # First two runs represent pre-match predictions, third run represents
        # calling 'tip' after those matches were played
        mock_data_import.fetch_match_results_data = Mock(
            side_effect=match_results_return_values
        )

        # Not fetching data, because it takes forever
        self.tip_command = tip.Command(fetch_data=False, data_importer=mock_data_import)

    def test_handle(self):
        with freeze_time("2016-01-01"):
            with self.subTest("with no existing match records in DB"):
                self.assertEqual(Match.objects.count(), 0)
                self.assertEqual(TeamMatch.objects.count(), 0)
                self.assertEqual(Prediction.objects.count(), 0)

                self.tip_command.handle(verbose=0)

                self.assertEqual(Match.objects.count(), ROW_COUNT)
                self.assertEqual(TeamMatch.objects.count(), ROW_COUNT * 2)
                self.assertEqual(Prediction.objects.count(), ROW_COUNT)

            with self.subTest("with the match records already saved in the DB"):
                self.assertEqual(Match.objects.count(), ROW_COUNT)
                self.assertEqual(TeamMatch.objects.count(), ROW_COUNT * 2)
                self.assertEqual(Prediction.objects.count(), ROW_COUNT)

                self.tip_command.handle(verbose=0)

                Prediction.update_or_create_from_data.assert_called()

                self.assertEqual(Match.objects.count(), ROW_COUNT)
                self.assertEqual(TeamMatch.objects.count(), ROW_COUNT * 2)

        with freeze_time("2017-01-01"):
            with self.subTest("with scoreless matches from ealier rounds"):
                right_now = datetime.now(tz=MELBOURNE_TIMEZONE)
                self.tip_command.right_now = right_now

                self.assertEqual(TeamMatch.objects.filter(score__gt=0).count(), 0)
                self.assertEqual(Prediction.objects.filter(is_correct=True).count(), 0)

                self.tip_command.handle(verbose=0)

                self.assertEqual(
                    TeamMatch.objects.filter(
                        match__start_date_time__lt=right_now, score=0
                    ).count(),
                    0,
                )
                self.assertGreater(
                    Prediction.objects.filter(
                        match__start_date_time__lt=right_now, is_correct=True
                    ).count(),
                    0,
                )

    @staticmethod
    def __update_or_create_from_data(update_or_create_from_data):
        return update_or_create_from_data


@skipIf(
    os.getenv("CI") == "true",
    "Useful test for subtle, breaking changes, but way too long to run in CI. "
    "Run manually on your machine to be safe",
)
class TestTipEndToEnd(TestCase):
    def setUp(self):
        MLModelFactory(name="tipresias")

        for team_name in TEAM_NAMES:
            TeamFactory(name=team_name)

        self.tip_command = tip.Command(ml_models="tipresias")

    def test_handle(self):
        self.assertEqual(Match.objects.count(), 0)
        self.assertEqual(TeamMatch.objects.count(), 0)
        self.assertEqual(Prediction.objects.count(), 0)

        self.tip_command.handle(verbose=0)

        match_count = Match.objects.count()

        self.assertGreater(match_count, 0)
        self.assertEqual(TeamMatch.objects.count(), match_count * 2)
        self.assertEqual(Prediction.objects.count(), match_count)
