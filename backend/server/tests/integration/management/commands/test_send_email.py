# pylint: disable=missing-docstring
from unittest.mock import patch

from django.test import TestCase
from django.utils import timezone
from faker import Faker
import numpy as np
from freezegun import freeze_time

from server.management.commands import send_email
from server.models import MLModel
from server.tests.fixtures.data_factories import fake_match_results_data
from server.tests.fixtures.factories import FullMatchFactory

FAKE = Faker()
PREDICTION_YEAR = 2016


class TestSendEmail(TestCase):
    fixtures = ["ml_models.json"]

    def setUp(self):
        self.match_results_data = fake_match_results_data(
            (PREDICTION_YEAR, PREDICTION_YEAR + 1)
        )

        ml_models = [
            MLModel.objects.get(is_principal=True),
            MLModel.objects.filter(
                is_principal=False, used_in_competitions=True
            ).first(),
        ]

        for match_data in self.match_results_data.to_dict("records"):
            match_date = timezone.localtime(match_data["date"].to_pydatetime())
            match_attrs = {
                "start_date_time": match_date,
                "round_number": match_data["round_number"],
                "venue": match_data["venue"],
            }
            prediction_attrs = {
                "prediction__ml_model": ml_models[0],
                "prediction__predicted_winner__name": np.random.choice(
                    [match_data["home_team"], match_data["away_team"]]
                ),
                "prediction_two__ml_model": ml_models[1],
                "prediction_two__predicted_winner__name": np.random.choice(
                    [match_data["home_team"], match_data["away_team"]]
                ),
            }
            team_match_attrs = {
                "home_team_match__team__name": match_data["home_team"],
                "away_team_match__team__name": match_data["away_team"],
                "home_team_match__score": match_data["home_score"],
                "away_team_match__score": match_data["away_score"],
            }
            FullMatchFactory(
                with_predictions=True,
                **match_attrs,
                **prediction_attrs,
                **team_match_attrs,
            )

        self.send_email_command = send_email.Command()

    @freeze_time(f"{PREDICTION_YEAR}-01-01")
    def test_handle(self):
        with patch("sendgrid.SendGridAPIClient") as MockClient:
            MockClient.return_value.client.return_value.mail.return_value.send.return_value.post = (
                lambda x: x
            )

            with patch.dict(
                "os.environ",
                {"EMAIL_RECIPIENT": "test@test.com", "SENDGRID_API_KEY": "test"},
            ):
                self.send_email_command.handle()

                MockClient.assert_called()
