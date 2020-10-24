# pylint: disable=missing-docstring

from datetime import datetime, timedelta, date

from freezegun import freeze_time
from django.test import TestCase
from django.utils import timezone
from candystore import CandyStore

from server.models import Match, TeamMatch, Prediction
from server import api
from server.tests.fixtures import data_factories, factories


TODAY = date.today()
CURRENT_YEAR = TODAY.year
CURRENT_YEAR_RANGE = (CURRENT_YEAR, CURRENT_YEAR + 1)

TIP_SEASON_RANGE = (2016, 2018)
TIP_DATES = [
    timezone.make_aware(datetime(season, 1, 1)) for season in range(*TIP_SEASON_RANGE)
]


class TestApi(TestCase):
    def setUp(self):
        self.ml_model = factories.MLModelFactory(
            name="test_estimator", is_principal=True, used_in_competitions=True
        )

        candy = CandyStore(seasons=TIP_SEASON_RANGE)
        fixtures = data_factories.fake_fixture_data(
            fixtures=candy.fixtures(to_dict=None)
        )
        predictions = data_factories.fake_prediction_data(
            match_data=candy.fixtures(to_dict=None)
        )
        match_results = data_factories.fake_match_results_data(
            match_results=candy.match_results(to_dict=None)
        )

        self.fixture_data = [
            fixtures.query("year == @season") for season in range(*TIP_SEASON_RANGE)
        ]
        self.prediction_data = [
            predictions.query("year == @season") for season in range(*TIP_SEASON_RANGE)
        ]
        self.match_results_data = [
            match_results.query("year == @season")
            for season in range(*TIP_SEASON_RANGE)
        ]

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
        MATCH_COUNT = 5
        # FullMatchFactory produces two predictions per match by default
        N_PREDICTION_MODELS = 2

        for idx in range(MATCH_COUNT * 2):
            factories.FullMatchFactory(future=(idx % 2 == 0), with_predictions=True)

        future_matches = Match.objects.filter(start_date_time__gt=timezone.now())
        next_match = min(future_matches, key=lambda match: match.start_date_time)

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
