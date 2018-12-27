from datetime import datetime, timezone, timedelta
from unittest.mock import Mock
from django.test import TestCase
from faker import Faker
import pandas as pd

from server.data_processors import FitzroyDataReader
from server.models import Match, TeamMatch, Team
from server.management.commands import tip

FAKE = Faker()
ROW_COUNT = 5


class TestTip(TestCase):
    def setUp(self):
        tomorrow = datetime.now(timezone.utc) + timedelta(days=1)
        year = tomorrow.year
        self.fixture_data = [
            {
                "date": pd.Timestamp(tomorrow),
                "season": year,
                "season_game": 1,
                "round": 1,
                "home_team": FAKE.company(),
                "away_team": FAKE.company(),
                "venue": FAKE.city(),
            }
            for _ in range(ROW_COUNT)
        ]
        fitzroy = FitzroyDataReader()
        fitzroy.get_fixture = Mock(return_value=pd.DataFrame(self.fixture_data))

        self.tip_command = tip.Command(data_reader=fitzroy)

        for match_data in self.fixture_data:
            Team(name=match_data["home_team"]).save()
            Team(name=match_data["away_team"]).save()

    def test_handle(self):
        with self.subTest("with no existing match records in DB"):
            self.assertEqual(len(Match.objects.all()), len(TeamMatch.objects.all()), 0)
            self.tip_command.handle()
            self.assertEqual(len(Match.objects.all()), ROW_COUNT)
            self.assertEqual(len(TeamMatch.objects.all()), ROW_COUNT * 2)

        with self.subTest("with the match records already saved in the DB"):
            self.assertEqual(len(Match.objects.all()), ROW_COUNT)
            self.assertEqual(len(TeamMatch.objects.all()), ROW_COUNT * 2)
            self.tip_command.handle()
            self.assertEqual(len(Match.objects.all()), ROW_COUNT)
            self.assertEqual(len(TeamMatch.objects.all()), ROW_COUNT * 2)
