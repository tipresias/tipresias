# pylint: disable=missing-docstring

from unittest.mock import MagicMock, patch

from django.test import Client, TestCase
from django.urls import reverse
import pandas as pd

from server.tests.fixtures import data_factories, factories
from server.models import Prediction, MLModel
from data.tipping import Tipper


N_MATCHES = 9


class TestUrls(TestCase):
    fixtures = ["ml_models.json"]

    def setUp(self):
        self.client = Client()

    @patch("server.views.Tipper")
    def test_predictions(self, mock_tipper_class):
        mock_tipper = Tipper()
        mock_tipper.submit_tips = MagicMock()
        mock_tipper_class.return_value = mock_tipper

        ml_model = MLModel.objects.get(is_principal=True)
        matches = [factories.FullMatchFactory() for _ in range(N_MATCHES)]
        prediction_data = pd.concat(
            [
                data_factories.fake_prediction_data(
                    match_data=match, ml_model_name=ml_model.name
                )
                for match in matches
            ]
        )
        predictions = {
            "data": prediction_data.to_dict("records"),
        }

        self.assertEqual(Prediction.objects.count(), 0)

        self.client.post(
            reverse("predictions"), content_type="application/json", data=predictions
        )

        # It creates predictions
        self.assertEqual(Prediction.objects.count(), N_MATCHES)
        # It submits tips
        mock_tipper.submit_tips.assert_called()
