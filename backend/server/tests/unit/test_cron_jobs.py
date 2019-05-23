from unittest.mock import Mock, patch
from datetime import datetime

from django.test import TestCase
from freezegun import freeze_time

from server.cron_jobs import SendTips
from server.tests.fixtures.data_factories import fake_fixture_data
from machine_learning.data_import import FitzroyDataImporter

THURSDAY = "2019-3-28"
FRIDAY = "2019-3-29"
SATURDAY = "2019-3-30"
SUNDAY = "2019-3-31"
SEVEN_PM = 19
MELBOURNE_TIMEZONE_OFFSET = 11
ROW_COUNT = 3


class TestSendTips(TestCase):
    def setUp(self):
        friday_args = [int(date_str) for date_str in FRIDAY.split("-")]
        friday = datetime(*friday_args, SEVEN_PM)

        saturday_args = [int(date_str) for date_str in SATURDAY.split("-")]
        saturday = datetime(*saturday_args, SEVEN_PM)

        sunday_args = [int(date_str) for date_str in SUNDAY.split("-")]
        sunday = datetime(*sunday_args, SEVEN_PM)

        days = [friday, saturday, sunday]

        year = friday.year
        fixture_data = fake_fixture_data(ROW_COUNT, (year, year + 1))

        for idx, day in enumerate(days):
            fixture_data.loc[idx, "date"] = day

        self.data_reader = FitzroyDataImporter()
        self.data_reader.fetch_fixtures = Mock(return_value=fixture_data)

    def test_do(self):
        with patch("server.management.commands.tip.Command") as MockTipCommand:
            MockTipCommand.return_value.handle = Mock()
            with patch(
                "server.management.commands.send_email.Command"
            ) as MockSendCommand:
                MockSendCommand.return_value.handle = Mock()

                # Need to create a new instance of SendTips with each freeze_time,
                # because the datetime is set in __init__
                with freeze_time(FRIDAY, tz_offset=MELBOURNE_TIMEZONE_OFFSET):
                    with self.subTest("on Friday with a match"):
                        SendTips(verbose=0, data_reader=self.data_reader).do()

                        MockTipCommand().handle.assert_called()
                        MockSendCommand().handle.assert_called()

                        MockTipCommand().handle.reset_mock()
                        MockSendCommand().handle.reset_mock()

                with freeze_time(THURSDAY, tz_offset=MELBOURNE_TIMEZONE_OFFSET):
                    with self.subTest("on Thursday without a match"):
                        SendTips(verbose=0, data_reader=self.data_reader).do()

                        MockTipCommand().handle.assert_not_called()
                        MockSendCommand().handle.assert_not_called()

                with freeze_time(SATURDAY, tz_offset=MELBOURNE_TIMEZONE_OFFSET):
                    with self.subTest("on Saturday with a match"):
                        SendTips(verbose=0, data_reader=self.data_reader).do()

                        MockTipCommand().handle.assert_not_called()
                        MockSendCommand().handle.assert_not_called()
