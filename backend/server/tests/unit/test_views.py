# pylint: disable=missing-docstring

from django.test import TestCase, RequestFactory
import pandas as pd

from server.tests.fixtures import data_factories, factories
from server.models import Prediction
from server import views

N_MATCHES = 9


class TestViews(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.ml_model = factories.MLModelFactory(name="test_estimator")
        self.matches = [factories.FullMatchFactory() for _ in range(N_MATCHES)]

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

            print(new_predicted_margins)
            # print(predictions)

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
