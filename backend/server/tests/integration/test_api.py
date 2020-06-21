# pylint: disable=missing-docstring

from unittest.mock import patch
from datetime import datetime, timedelta

from freezegun import freeze_time
from django.test import TestCase
from django.utils import timezone
import pandas as pd

from data.helpers import pivot_team_matches_to_matches
from server.models import Match, TeamMatch, Prediction
from server import api
from server.tests.fixtures import data_factories, factories


ROW_COUNT = 5
TIP_DATES = [
    timezone.make_aware(datetime(2016, 1, 1)),
    timezone.make_aware(datetime(2017, 1, 1)),
]


class TestApi(TestCase):
    def setUp(self):
        self.ml_model = factories.MLModelFactory(
            name="test_estimator", is_principal=True, used_in_competitions=True
        )

        (self.fixture_data, self.prediction_data, self.match_results_data,) = zip(
            *[self._build_imported_data_mocks(tip_date) for tip_date in TIP_DATES]
        )

        self.api = api

    def test_update_fixture_data(self):
        with freeze_time(TIP_DATES[0]):
            right_now = timezone.now()  # pylint: disable=unused-variable
            min_future_round = (
                self.fixture_data[0].query("date > @right_now")["round_number"].min()
            )
            future_fixture_data = (
                self.fixture_data[0].query("date > @right_now").to_dict("records")
            )

            with self.subTest("with no existing match records in DB"):
                self.assertEqual(Match.objects.count(), 0)
                self.assertEqual(TeamMatch.objects.count(), 0)

                self.api.update_fixture_data(
                    future_fixture_data, min_future_round, verbose=0
                )

                # It creates records
                self.assertEqual(Match.objects.count(), ROW_COUNT)
                self.assertEqual(TeamMatch.objects.count(), ROW_COUNT * 2)

            with self.subTest("with the match records already saved in the DB"):
                self.assertEqual(Match.objects.count(), ROW_COUNT)
                self.assertEqual(TeamMatch.objects.count(), ROW_COUNT * 2)

                self.api.update_fixture_data(
                    future_fixture_data, min_future_round, verbose=0
                )

                # It doesn't create new records
                self.assertEqual(Match.objects.count(), ROW_COUNT)
                self.assertEqual(TeamMatch.objects.count(), ROW_COUNT * 2)

        with freeze_time(TIP_DATES[1]):
            right_now = timezone.now()  # pylint: disable=unused-variable
            min_future_round = (
                self.fixture_data[1].query("date > @right_now")["round_number"].min()
            )
            future_fixture_data = (
                self.fixture_data[1].query("date > @right_now").to_dict("records")
            )

            with self.subTest("with past matches in the data"):
                with self.assertRaisesRegex(
                    AssertionError, "Expected future matches only"
                ):
                    self.api.update_fixture_data(
                        self.fixture_data[0].to_dict("records"),
                        min_future_round,
                        verbose=0,
                    )

    @patch("data.data_import.fetch_match_results_data")
    def test_backfill_recent_match_results(self, mock_fetch_match_results_data):
        mock_fetch_match_results_data.return_value = self.match_results_data[0]

        for fixture_datum in self.fixture_data[0].to_dict("records"):
            match = Match.get_or_create_from_raw_data(fixture_datum)
            TeamMatch.get_or_create_from_raw_data(match, fixture_datum)

        with freeze_time(TIP_DATES[1]):
            self.assertEqual(TeamMatch.objects.filter(score__gt=0).count(), 0)
            self.assertEqual(Prediction.objects.filter(is_correct=True).count(), 0)

            self.api.backfill_recent_match_results(verbose=0)

            # It updates scores for past matches
            self.assertEqual(
                TeamMatch.objects.filter(
                    match__start_date_time__lt=timezone.now(), score=0
                ).count(),
                0,
            )

    def test_fetch_next_match(self):
        factories.MatchFactory(year=timezone.now().year - 1)

        with self.subTest("without any future matches"):
            next_match = self.api.fetch_next_match()

            # It returns None
            self.assertEqual(next_match, None)

        next_match_record = factories.MatchFactory(future=True)
        factories.MatchFactory(year=timezone.now().year + 1)

        next_match = self.api.fetch_next_match()

        # It returns the next match to be played
        self.assertEqual(
            next_match,
            {
                "round_number": next_match_record.round_number,
                "season": next_match_record.start_date_time.year,
            },
        )

    def test_update_future_match_predictions(self):
        for fixture_datum in self.fixture_data[0].to_dict("records"):
            match = Match.get_or_create_from_raw_data(fixture_datum)
            TeamMatch.get_or_create_from_raw_data(match, fixture_datum)

        prediction_data = pivot_team_matches_to_matches(self.prediction_data[0])

        with self.subTest("when the predictions are for past matches"):
            with freeze_time(TIP_DATES[1]):
                self.assertEqual(Prediction.objects.count(), 0)

                self.api.update_future_match_predictions(
                    prediction_data.to_dict("records")
                )

                # It doesn't create any prediction records
                self.assertEqual(Prediction.objects.count(), 0)

        with freeze_time(TIP_DATES[0]):
            self.api.update_future_match_predictions(prediction_data.to_dict("records"))

            # It creates prediction records
            self.assertEqual(Prediction.objects.count(), ROW_COUNT)

    def _build_imported_data_mocks(self, tip_date):
        with freeze_time(tip_date):
            tomorrow = timezone.localtime() + timedelta(days=1)
            year = tomorrow.year

            # Mock footywire fixture data
            fixture_data = data_factories.fake_fixture_data(ROW_COUNT, (year, year + 1))

            prediction_match_data, _ = zip(
                *[
                    (
                        self._build_prediction_and_match_results_data(match_data),
                        self._build_teams(match_data),
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

    def _build_prediction_and_match_results_data(self, match_data):
        match_predictions = data_factories.fake_prediction_data(
            match_data=match_data, ml_model_name=self.ml_model.name
        )

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

    @staticmethod
    def _build_teams(match_data):
        factories.TeamFactory(name=match_data["home_team"])
        factories.TeamFactory(name=match_data["away_team"])
