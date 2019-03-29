from unittest.mock import Mock, patch
from datetime import date, datetime

from django.test import TestCase
from freezegun import freeze_time
import pandas as pd

from server.cron_jobs import SendTips
from server.data_readers import FootywireDataReader

THURSDAY = "2019-3-28"
FRIDAY = "2019-3-29"
SATURDAY = "2019-3-30"
SEVEN_O_CLOCK = 7


class TestSendTips(TestCase):
    def setUp(self):
        friday_args = [int(date_str) for date_str in FRIDAY.split("-")]
        friday = date(*friday_args)
        year = friday.year
        fixture_data_frame = pd.DataFrame(
            [
                {
                    "date": datetime(year, friday.month, friday.day, SEVEN_O_CLOCK),
                    "home_team": "Richmond",
                    "away_team": "Carlton",
                    "home_score": 0,
                    "away_score": 0,
                    "venue": "MCG",
                    "crowd": 0,
                    "round_label": "Round 1",
                    "round": 1,
                    "season": year,
                },
                {
                    "date": datetime(year, friday.month, friday.day + 1, SEVEN_O_CLOCK),
                    "home_team": "Melbourne",
                    "away_team": "Sydney",
                    "home_score": 0,
                    "away_score": 0,
                    "venue": "MCG",
                    "crowd": 0,
                    "round_label": "Round 1",
                    "round": 1,
                    "season": year,
                },
            ]
        )

        data_reader = FootywireDataReader()
        data_reader.get_fixture = Mock(return_value=fixture_data_frame)

        self.job = SendTips(data_reader=data_reader)

    def test_do(self):
        with patch("server.management.commands.tip.Command") as MockTipCommand:
            MockTipCommand.return_value.handle = Mock()
            with patch(
                "server.management.commands.send_email.Command"
            ) as MockSendCommand:
                MockSendCommand.return_value.handle = Mock()

                with freeze_time(FRIDAY):
                    with self.subTest("on Friday with a match"):
                        self.job.do()

                        MockTipCommand.handle.assert_called()
                        MockSendCommand.handle.assert_called()

                with freeze_time(THURSDAY):
                    with self.subTest("on Thursday without a match"):
                        self.job.do()

                        MockTipCommand.handle.assert_not_called()
                        MockSendCommand.handle.assert_not_called()

                with freeze_time(SATURDAY):
                    with self.subTest("on Saturday with a match"):
                        self.job.do()

                        MockTipCommand.handle.assert_not_called()
                        MockSendCommand.handle.assert_not_called()
