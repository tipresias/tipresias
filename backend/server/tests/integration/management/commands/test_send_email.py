from datetime import datetime, timezone
from unittest.mock import patch

from django.test import TestCase
from faker import Faker

from server.data_config import TEAM_NAMES
from server.models import Match, Team, TeamMatch, Prediction, MLModel
from server.management.commands import send_email
from project.settings.common import MELBOURNE_TIMEZONE

FAKE = Faker()
ROW_COUNT = 10


class TestSendEmail(TestCase):
    def setUp(self):
        today = datetime.now(tz=MELBOURNE_TIMEZONE)
        year = today.year
        team_names = TEAM_NAMES[:]

        self.fixture_data = [
            {
                "date": today,
                "season": year,
                "round": 1,
                "round_label": "Round 1",
                "crowd": 1234,
                "home_team": team_names.pop(),
                "away_team": team_names.pop(),
                "home_score": 50,
                "away_score": 100,
                "venue": FAKE.city(),
            }
            for idx in range(ROW_COUNT)
        ]

        # Save records in DB
        ml_model = MLModel(name="tipresias")
        ml_model.save()

        for match_data in self.fixture_data:
            match = Match(
                start_date_time=match_data["date"],
                round_number=match_data["round"],
                venue=match_data["venue"],
            )
            match.save()

            home_team = Team(name=match_data["home_team"])
            home_team.save()
            away_team = Team(name=match_data["away_team"])
            away_team.save()

            home_team_match = TeamMatch(
                team=home_team,
                match=match,
                at_home=True,
                score=match_data["home_score"],
            )
            home_team_match.save()
            away_team_match = TeamMatch(
                team=away_team,
                match=match,
                at_home=False,
                score=match_data["away_score"],
            )
            away_team_match.save()

            Prediction(
                ml_model=ml_model,
                match=match,
                predicted_winner=home_team,
                predicted_margin=50,
            ).save()

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
