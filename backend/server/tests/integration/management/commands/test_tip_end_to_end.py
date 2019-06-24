from django.test import TestCase

from server.models import Match, TeamMatch, Prediction
from server import data_import
from server.management.commands import tip
from server.tests.fixtures.factories import MLModelFactory, TeamFactory


class TestTipEndToEnd(TestCase):
    def setUp(self):
        MLModelFactory(name="tipresias")

        for team_name in data_import.fetch_data_config().get("team_names"):
            TeamFactory(name=team_name)

        self.tip_command = tip.Command(ml_models="tipresias")

    def test_handle(self):
        self.assertEqual(Match.objects.count(), 0)
        self.assertEqual(TeamMatch.objects.count(), 0)
        self.assertEqual(Prediction.objects.count(), 0)

        self.tip_command.handle(verbose=0)

        match_count = Match.objects.count()

        self.assertGreater(match_count, 0)
        self.assertEqual(TeamMatch.objects.count(), match_count * 2)
        self.assertEqual(Prediction.objects.count(), match_count)
