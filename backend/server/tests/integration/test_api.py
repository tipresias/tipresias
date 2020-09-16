# pylint: disable=missing-docstring

from datetime import datetime, timedelta

from freezegun import freeze_time
from django.test import TestCase
from django.utils import timezone
import pandas as pd

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

        (
            self.fixture_data,
            self.prediction_data,
            self.match_results_data,
        ) = zip(*[self._build_imported_data_mocks(tip_date) for tip_date in TIP_DATES])

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
                self.assertEqual(Match.objects.count(), len(future_fixture_data))
                self.assertEqual(
                    TeamMatch.objects.count(), len(future_fixture_data) * 2
                )

            with self.subTest("with the match records already saved in the DB"):
                self.assertEqual(Match.objects.count(), len(future_fixture_data))
                self.assertEqual(
                    TeamMatch.objects.count(), len(future_fixture_data) * 2
                )

                self.api.update_fixture_data(
                    future_fixture_data, min_future_round, verbose=0
                )

                # It doesn't create new records
                self.assertEqual(Match.objects.count(), len(future_fixture_data))
                self.assertEqual(
                    TeamMatch.objects.count(), len(future_fixture_data) * 2
                )

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

    def test_backfill_recent_match_results(self):
        for fixture_datum in self.fixture_data[0].to_dict("records"):
            match = Match.get_or_create_from_raw_data(fixture_datum)
            TeamMatch.get_or_create_from_raw_data(match, fixture_datum)

        with freeze_time(TIP_DATES[1]):
            self.assertEqual(TeamMatch.objects.filter(score__gt=0).count(), 0)
            self.assertEqual(Prediction.objects.filter(is_correct=True).count(), 0)

            self.api.backfill_recent_match_results(
                self.match_results_data[0].to_dict("records"), verbose=0
            )

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
        prediction_data = self.prediction_data[0].to_dict("records")

        with self.subTest("when there are no future matches"):
            with self.assertRaisesRegex(AssertionError, r"No future matches exist"):
                self.api.update_future_match_predictions(prediction_data)

        for fixture_datum in self.fixture_data[0].to_dict("records"):
            match = Match.get_or_create_from_raw_data(fixture_datum)
            TeamMatch.get_or_create_from_raw_data(match, fixture_datum)

        with self.subTest("when the predictions are for past matches"):
            with freeze_time(TIP_DATES[1]):
                # Need at least one future match to avoid errors
                factories.MatchFactory(
                    start_date_time=(timezone.now() + timedelta(days=1))
                )

                self.assertEqual(Prediction.objects.count(), 0)

                self.api.update_future_match_predictions(prediction_data)

                # It doesn't create any prediction records
                self.assertEqual(Prediction.objects.count(), 0)

        with freeze_time(TIP_DATES[0]):
            self.api.update_future_match_predictions(prediction_data)

            # It creates prediction records
            self.assertEqual(Prediction.objects.count(), len(self.fixture_data[0]))

    def fetch_latest_round_predictions(self):
        # FullMatchFactory produces two predictions per match by default
        N_PREDICTION_MODELS = 2

        for idx in range(ROW_COUNT * 2):
            factories.FullMatchFactory(future=(idx % 2 == 0), with_predictions=True)

        next_match = (
            Match.objects.filter(start_date_time__gt=timezone.now())
            .order_by("start_date_time")
            .first()
        )

        latest_predictions = self.api.fetch_latest_round_predictions()
        latest_matches = Match.objects.filter(
            start_date_time__year=next_match.year, round_number=next_match.round_number
        )

        # It fetches predictions for matches (future or past) from the same round
        # as the next match (i.e. current round if mid-round next round
        # if between rounds)
        self.assertEqual(
            latest_matches.count(), len(latest_predictions) / N_PREDICTION_MODELS
        )

    def _build_imported_data_mocks(self, tip_date):
        with freeze_time(tip_date):
            tomorrow = timezone.localtime() + timedelta(days=1)
            year = tomorrow.year

            # Mock footywire fixture data
            fixture_data = data_factories.fake_fixture_data((year, year + 1))

            prediction_match_data, _ = zip(
                *[
                    (
                        self._build_prediction_and_match_results_data(match_data),
                        self._build_teams(match_data),
                    )
                    for match_data in fixture_data
                ]
            )

            prediction_data, match_results_data = zip(*prediction_match_data)

        return (
            pd.DataFrame(fixture_data),
            pd.concat(prediction_data),
            pd.DataFrame(list(match_results_data)),
        )

    def _build_prediction_and_match_results_data(self, fixture_data):
        match_predictions = data_factories.fake_prediction_data(
            match_data=fixture_data, ml_model_name=self.ml_model.name
        )

        return (
            match_predictions,
            self._build_match_results_data(fixture_data, match_predictions),
        )

    @staticmethod
    def _build_match_results_data(fixture_data, match_predictions):
        # Making all predictions correct, because trying to get fancy with it
        # resulted in flakiness that was difficult to fix
        return {
            "date": fixture_data["date"],
            "year": fixture_data["year"],
            "round_number": fixture_data["round_number"],
            "home_team": fixture_data["home_team"],
            "away_team": fixture_data["away_team"],
            "home_score": match_predictions["home_predicted_margin"].iloc[0],
            "away_score": match_predictions["away_predicted_margin"].iloc[0],
        }

    @staticmethod
    def _build_teams(match_data):
        factories.TeamFactory(name=match_data["home_team"])
        factories.TeamFactory(name=match_data["away_team"])
