from datetime import datetime
from unittest.mock import patch

from django.test import TestCase
from faker import Faker
import numpy as np

from server.management.commands import send_email
from server.tests.fixtures.data_factories import fake_footywire_fixture_data
from server.tests.fixtures.factories import MLModelFactory, FullMatchFactory
from project.settings.common import MELBOURNE_TIMEZONE

FAKE = Faker()
ROW_COUNT = 10


class TestSendEmail(TestCase):
    def setUp(self):
        today = datetime.now(tz=MELBOURNE_TIMEZONE)
        year = today.year

        self.fixture_data = fake_footywire_fixture_data(ROW_COUNT, (year, year + 1))

        # Save records in DB
        ml_model = MLModelFactory(name="tipresias")

        for match_data in self.fixture_data.to_dict("records"):
            match_date = (
                match_data["date"].to_pydatetime().replace(tzinfo=MELBOURNE_TIMEZONE)
            )
            match_attrs = {
                "start_date_time": match_date,
                "round_number": match_data["round"],
                "venue": match_data["venue"],
            }
            prediction_attrs = {
                "prediction__ml_model": ml_model,
                "prediction__predicted_winner__name": np.random.choice(
                    [match_data["home_team"], match_data["away_team"]]
                ),
            }
            team_match_attrs = {
                "home_team_match__team__name": match_data["home_team"],
                "away_team_match__team__name": match_data["away_team"],
                "home_team_match__score": match_data["home_score"],
                "away_team_match__score": match_data["away_score"],
            }
            FullMatchFactory(**match_attrs, **prediction_attrs, **team_match_attrs)

        self.send_email_command = send_email.Command()

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
