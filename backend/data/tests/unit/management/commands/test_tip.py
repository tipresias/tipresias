# pylint: disable=missing-docstring

from unittest.mock import MagicMock

from django.test import TestCase

from data.management.commands import tip
from data.tipping import Tipper


class TestTip(TestCase):
    def setUp(self):
        self.tipper = Tipper(verbose=0)
        self.tipper.fetch_upcoming_fixture = MagicMock()
        self.tipper.update_match_predictions = MagicMock()
        self.tipper.submit_tips = MagicMock()

        self.tipper_class = MagicMock(return_value=self.tipper)
        self.tip_command = tip.Command()

    def test_handle(self):
        self.tip_command.handle(tipper_class=self.tipper_class, verbose=0)

        # It fetches fixture data
        self.tipper.fetch_upcoming_fixture.assert_called()
        # It requests predictions
        self.tipper.update_match_predictions.assert_called()
        # It submits tips
        self.tipper.submit_tips.assert_called()
