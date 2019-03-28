from unittest.mock import Mock, patch
from django.test import TestCase

from server.cron_jobs import SendTips


class TestSendTips(TestCase):
    def setUp(self):
        self.job = SendTips()

    def test_do(self):
        with patch("server.management.commands.tip.Command") as MockTipCommand:
            MockTipCommand.return_value.handle = Mock()
            with patch(
                "server.management.commands.send_email.Command"
            ) as MockSendCommand:
                MockSendCommand.return_value.handle = Mock()
                self.job.do()

                MockTipCommand.handle.assert_called()
                MockSendCommand.handle.assert_called()
