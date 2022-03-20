# pylint: disable=missing-docstring

import json

from django.test import TestCase, RequestFactory
from django.utils import timezone
import pandas as pd
import numpy as np
from freezegun import freeze_time

from server.tests.fixtures import data_factories, factories
from server.models import Prediction, Match, TeamMatch
from server import views

N_MATCHES = 9
CURRENT_YEAR = timezone.now().year
CURRENT_YEAR_RANGE = (CURRENT_YEAR, CURRENT_YEAR + 1)
APR = 4
SEPT = 9
# We reduce the range from that of a typical season to allow for some past
# and future matches (relative to match records) in imported data sets.
MONTH = np.random.randint(APR, SEPT)
DAY = np.random.randint(1, 31)
HOUR = np.random.randint(1, 24)

RIGHT_NOW = timezone.datetime(CURRENT_YEAR, MONTH, DAY, HOUR)


class TestViews(TestCase):
    @freeze_time(RIGHT_NOW)
    def setUp(self):
        self.factory = RequestFactory()
        self.ml_model = factories.MLModelFactory(
            name="test_estimator", is_principal=True, used_in_competitions=True
        )

        self.matches = [
            factories.FullMatchFactory(future=True, round_number=5)
            for _ in range(N_MATCHES)
        ]

        self.views = views

    def test_predictions(self):
        prediction_data = pd.concat(
            [
                data_factories.fake_prediction_data(
                    match_data=match, ml_model_name=self.ml_model.name
                )
                for match in self.matches
            ]
        )
        predictions = {
            "data": prediction_data.to_dict("records"),
        }

        self.assertEqual(Prediction.objects.count(), 0)

        with self.subTest("GET request"):
            request = self.factory.get(
                "/predictions", content_type="application/json", data=predictions
            )

            response = views.predictions(request)

            # It doesn't create predictions
            self.assertEqual(Prediction.objects.count(), 0)
            # It returns a 405 response
            self.assertEqual(response.status_code, 405)

        request = self.factory.post(
            "/predictions", content_type="application/json", data=predictions
        )

        with self.settings(API_TOKEN="token", ENVIRONMENT="production"):
            with self.subTest("when Authorization header doesn't match app token"):
                request.headers = {"Authorization": "Bearer not_token"}
                response = views.predictions(request)

                # It doesn't create predictions
                self.assertEqual(Prediction.objects.count(), 0)
                # It returns unauthorized response
                self.assertEqual(response.status_code, 401)

            with self.subTest("when Authorization header does match app token"):
                request.headers = {"Authorization": "Bearer token"}
                response = views.predictions(request)

                # It creates predictions
                self.assertEqual(Prediction.objects.count(), N_MATCHES)
                # It returns success response
                self.assertEqual(response.status_code, 200)
                # It returns the created predictions
                prediction_response = json.loads(response.content)
                self.assertEqual(len(prediction_response), N_MATCHES)
                for pred in prediction_response:
                    self.assertEqual(
                        {
                            "predicted_winner__name",
                            "predicted_margin",
                            "predicted_win_probability",
                        },
                        set(pred.keys()),
                    )

        with self.subTest("with existing prediction records"):
            original_predicted_margins = list(
                Prediction.objects.all().values_list("predicted_margin", flat=True)
            )

            for prediction in Prediction.objects.all():
                prediction.predicted_margin += 5
                prediction.save()

            new_predicted_margins = list(
                Prediction.objects.all().values_list("predicted_margin", flat=True)
            )

            self.assertNotEqual(
                set(original_predicted_margins), set(new_predicted_margins)
            )

            response = views.predictions(request)

            # It doesn't create any new predictions
            self.assertEqual(Prediction.objects.count(), N_MATCHES)
            # It updates existing predictions
            posted_predicted_margins = list(
                Prediction.objects.all().values_list("predicted_margin", flat=True)
            )
            self.assertEqual(
                set(original_predicted_margins), set(posted_predicted_margins)
            )
            # It returns a success response
            self.assertEqual(response.status_code, 200)
            # It returns the updated predictions
            prediction_response = json.loads(response.content)
            self.assertEqual(len(prediction_response), N_MATCHES)

            for pred in prediction_response:
                self.assertEqual(
                    {
                        "predicted_winner__name",
                        "predicted_margin",
                        "predicted_win_probability",
                    },
                    set(pred.keys()),
                )

            with self.subTest("when some matches have already been played"):
                second_match_date = (
                    pd.to_datetime(
                        prediction_data.sort_values("date", ascending=True)["date"]
                    )
                    .iloc[1]
                    .to_pydatetime()
                )

                with freeze_time(second_match_date):
                    original_predictions = sorted(
                        Prediction.objects.all().values(
                            "predicted_margin", "match__start_date_time"
                        ),
                        key=lambda pred: pred["match__start_date_time"],
                    )
                    original_predicted_margins = [
                        pred["predicted_margin"] for pred in original_predictions
                    ]

                    for prediction in Prediction.objects.all():
                        prediction.predicted_margin += 5
                        prediction.save()

                    new_predictions = sorted(
                        Prediction.objects.all().values(
                            "predicted_margin", "match__start_date_time"
                        ),
                        key=lambda pred: pred["match__start_date_time"],
                    )
                    new_predicted_margins = [
                        pred["predicted_margin"] for pred in new_predictions
                    ]

                    self.assertNotEqual(
                        original_predicted_margins, new_predicted_margins
                    )

                    response = views.predictions(request)

                    # It doesn't update predictions for played matches
                    played_match_prediction = min(
                        Prediction.objects.all(),
                        key=lambda pred: pred.match.start_date_time,
                    )
                    self.assertEqual(
                        new_predicted_margins[0],
                        played_match_prediction.predicted_margin,
                    )

    @freeze_time(RIGHT_NOW)
    def test_fixtures(self):
        right_now = timezone.now()  # pylint: disable=unused-variable
        max_match_round = max(
            Match.objects.all(), key=lambda match: match.round_number
        ).round_number
        fixture_data = (
            data_factories.fake_fixture_data(seasons=CURRENT_YEAR_RANGE)
            .query("date > @right_now")
            .assign(round_number=(max_match_round + 1))
        )

        fixtures = {
            "data": fixture_data.to_dict("records"),
            "upcoming_round": int(fixture_data["round_number"].min()),
        }

        self.assertEqual(Match.objects.count(), N_MATCHES)

        with self.subTest("GET request"):
            request = self.factory.get(
                "/fixtures", content_type="application/json", data=fixtures
            )

            response = views.fixtures(request, verbose=0)

            # It doesn't create fixtures
            self.assertEqual(Match.objects.count(), N_MATCHES)
            # It returns a 405 response
            self.assertEqual(response.status_code, 405)

        request = self.factory.post(
            "/fixtures", content_type="application/json", data=fixtures
        )

        with self.settings(API_TOKEN="token", ENVIRONMENT="production"):
            with self.subTest("when Authorization header doesn't match app token"):
                request.headers = {"Authorization": "Bearer not_token"}
                response = views.fixtures(request, verbose=0)

                # It doesn't create fixtures
                self.assertEqual(Match.objects.count(), N_MATCHES)
                # It returns unauthorized response
                self.assertEqual(response.status_code, 401)

            with self.subTest("when Authorization header does match app token"):
                request.headers = {"Authorization": "Bearer token"}
                response = views.fixtures(request, verbose=0)

                # It creates a future match per row of fixture data
                self.assertEqual(
                    Match.objects.filter().count(),
                    len(fixture_data) + N_MATCHES,
                )
                # It returns success response
                self.assertEqual(response.status_code, 200)

    def test_matches(self):
        match_results_data = [
            {
                "date": match.start_date_time,
                "year": match.start_date_time.year,
                "round": f"R{match.round_number}",
                "round_number": match.round_number,
                "home_team": match.teammatch_set.get(at_home=1).team.name,
                "away_team": match.teammatch_set.get(at_home=0).team.name,
                "venue": match.venue,
                "home_score": match.teammatch_set.get(at_home=1).score,
                "away_score": match.teammatch_set.get(at_home=0).score,
                "match_id": match.id,
                "crowd": np.random.randint(10000, 30000),
            }
            for match in self.matches
        ]
        matches = {"data": match_results_data}

        # Pretend the scores haven't been updated yet
        TeamMatch.objects.all().update(score=0)
        self.assertEqual(Match.objects.filter(teammatch__score__gt=0).count(), 0)

        with self.subTest("GET request"):
            request = self.factory.get(
                "/matches", content_type="application/json", data=matches
            )

            response = views.matches(request, verbose=0)

            # It update match scores
            self.assertEqual(Match.objects.filter(teammatch__score__gt=0).count(), 0)
            # It returns a 405 response
            self.assertEqual(response.status_code, 405)

        request = self.factory.post(
            "/matches", content_type="application/json", data=matches
        )

        with self.settings(API_TOKEN="token", ENVIRONMENT="production"):
            with self.subTest("when Authorization header doesn't match app token"):
                request.headers = {"Authorization": "Bearer not_token"}
                response = views.matches(request, verbose=0)

                # It doesn't update match scores
                self.assertEqual(
                    Match.objects.filter(teammatch__score__gt=0).count(), 0
                )
                # It returns unauthorized response
                self.assertEqual(response.status_code, 401)

            with self.subTest("when Authorization header does match app token"):
                request.headers = {"Authorization": "Bearer token"}
                response = views.matches(request, verbose=0)

                # It updates match scores
                self.assertEqual(
                    TeamMatch.objects.filter(score__gt=0).count(),
                    TeamMatch.objects.filter(
                        match__start_date_time__lt=timezone.now()
                    ).count(),
                )
                # It returns success response
                self.assertEqual(response.status_code, 200)
