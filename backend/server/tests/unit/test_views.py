# pylint: disable=missing-docstring

from django.test import TestCase, RequestFactory
from django.utils import timezone
import pandas as pd
import numpy as np

from server.tests.fixtures import data_factories, factories
from server.models import Prediction, Match, TeamMatch
from server import views

N_MATCHES = 9
YEAR_RANGE = (timezone.now().year, timezone.now().year + 1)


class TestViews(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.ml_model = factories.MLModelFactory(
            name="test_estimator", is_principal=True, used_in_competitions=True
        )
        self.matches = [factories.FullMatchFactory() for _ in range(N_MATCHES)]
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
                self.assertEqual(Prediction.objects.count(), 9)
                # It returns success response
                self.assertEqual(response.status_code, 200)

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

            self.assertNotEqual(original_predicted_margins, new_predicted_margins)

            response = views.predictions(request)

            # It doesn't create any new predictions
            self.assertEqual(Prediction.objects.count(), N_MATCHES)
            # It updates existing predictions
            posted_predicted_margins = list(
                Prediction.objects.all().values_list("predicted_margin", flat=True)
            )
            self.assertEqual(original_predicted_margins, posted_predicted_margins)
            # It returns a success response
            self.assertEqual(response.status_code, 200)

    def test_fixtures(self):
        max_round = Match.objects.order_by("-round_number").first().round_number
        fixture_data = data_factories.fake_fixture_data(N_MATCHES, YEAR_RANGE).assign(
            round_number=(max_round + 1)
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

                # It creates fixtures
                self.assertEqual(Match.objects.count(), N_MATCHES * 2)
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
