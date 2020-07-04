# pylint: disable=missing-docstring

from django.test import TestCase, RequestFactory
from django.utils import timezone
import pandas as pd

from server.tests.fixtures import data_factories, factories
from server.models import Prediction, Match
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
        fixture_data = data_factories.fake_fixture_data(N_MATCHES, YEAR_RANGE)
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
