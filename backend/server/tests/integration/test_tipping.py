# pylint: disable=missing-docstring
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock

from django.test import TestCase
from django.utils import timezone
from freezegun import freeze_time
import pandas as pd
from faker import Faker

from server.models import Match, TeamMatch, Prediction, MLModel
from server.tipping import Tipper, FootyTipsSubmitter
from server.tests.fixtures.data_factories import fake_fixture_data
from server.tests.fixtures.factories import (
    TeamFactory,
    FullMatchFactory,
    PredictionFactory,
    MLModelFactory,
)


ROW_COUNT = 5
TIP_DATES = [
    timezone.make_aware(datetime(2016, 1, 1)),
    timezone.make_aware(datetime(2017, 1, 1)),
]
FAKE = Faker()


class TestTipper(TestCase):
    @patch("server.data_import")
    def setUp(self, mock_data_import):  # pylint: disable=arguments-differ
        (fixture_return_values, match_results_return_values,) = zip(
            *[self._build_imported_data_mocks(tip_date) for tip_date in TIP_DATES]
        )

        # We have 2 subtests in 2016 and 1 in 2017, which requires 3 fixture
        # and prediction data imports, but only 1 match results data import,
        # because it doesn't get called until 2017
        mock_data_import.request_predictions = Mock(
            side_effect=self._request_predictions
        )
        mock_data_import.fetch_fixture_data = Mock(
            side_effect=fixture_return_values[:1] + fixture_return_values
        )
        mock_data_import.fetch_match_results_data = Mock(
            return_value=match_results_return_values[0]
        )

        self.tipping = Tipper(data_importer=mock_data_import, verbose=0,)

    def test_update_match_data(self):
        with freeze_time(TIP_DATES[0]):
            right_now = timezone.localtime()
            self.tipping._right_now = right_now  # pylint: disable=protected-access

            with self.subTest("with no existing match records in DB"):
                self.assertEqual(Match.objects.count(), 0)
                self.assertEqual(TeamMatch.objects.count(), 0)

                self.tipping.update_match_data()

                self.assertEqual(Match.objects.count(), ROW_COUNT)
                self.assertEqual(TeamMatch.objects.count(), ROW_COUNT * 2)

            with self.subTest("with the match records already saved in the DB"):
                self.assertEqual(Match.objects.count(), ROW_COUNT)
                self.assertEqual(TeamMatch.objects.count(), ROW_COUNT * 2)

                self.tipping.update_match_data()

                self.assertEqual(Match.objects.count(), ROW_COUNT)
                self.assertEqual(TeamMatch.objects.count(), ROW_COUNT * 2)

        with freeze_time(TIP_DATES[1]):
            with self.subTest("with scoreless matches from ealier rounds"):
                right_now = timezone.localtime()
                self.tipping._right_now = right_now  # pylint: disable=protected-access

                self.assertEqual(TeamMatch.objects.filter(score__gt=0).count(), 0)
                self.assertEqual(Prediction.objects.filter(is_correct=True).count(), 0)

                self.tipping.update_match_data()

                self.assertEqual(
                    TeamMatch.objects.filter(
                        match__start_date_time__lt=right_now, score=0
                    ).count(),
                    0,
                )

    def test_request_predictions(self):
        with freeze_time(TIP_DATES[0]):
            right_now = timezone.localtime()
            self.tipping._right_now = right_now  # pylint: disable=protected-access

            with self.subTest("with no existing match records in DB"):
                self.assertEqual(Match.objects.count(), 0)

                self.tipping.request_predictions()

                self.tipping.data_importer.request_predictions.assert_not_called()
                self.assertEqual(Prediction.objects.count(), 0)

            with self.subTest("with upcoming match records saved in the DB"):
                for _ in range(ROW_COUNT):
                    FullMatchFactory(future=True)

                self.tipping.request_predictions()

                self.tipping.data_importer.request_predictions.assert_called()
                self.assertEqual(Prediction.objects.count(), 0)

    def test_submit_tips(self):
        MLModelFactory(is_principle=True, used_in_competitions=True)

        for _ in range(ROW_COUNT):
            FullMatchFactory(future=True)

        mock_submitter = FootyTipsSubmitter(browser=None)
        mock_submitter.submit_tips = MagicMock()

        with self.subTest("when there are no predictions to submit"):
            self.tipping.submit_tips(tip_submitters=[mock_submitter])

            # It doesn't try to submit any tips
            mock_submitter.submit_tips.assert_not_called()

        ml_model = MLModel.objects.get(is_principle=True)

        for match in Match.objects.all():
            # Need to use competition models for the predictions to get queried
            PredictionFactory(match=match, ml_model=ml_model)

        self.tipping.submit_tips(tip_submitters=[mock_submitter, mock_submitter])

        # It submits tips to all competitions
        self.assertEqual(mock_submitter.submit_tips.call_count, 2)

    def _build_imported_data_mocks(self, tip_date):
        with freeze_time(tip_date):
            tomorrow = timezone.localtime() + timedelta(days=1)
            year = tomorrow.year

            # Mock footywire fixture data
            fixture_data = fake_fixture_data(ROW_COUNT, (year, year + 1))

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
        TeamFactory(name=match_data["home_team"])
        TeamFactory(name=match_data["away_team"])

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
