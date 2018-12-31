# TODO: After refactoring, mock the bejeezus out of this test with a basic linear
# model and fake data, because this is getting closer to an integration test with
# each import

from datetime import datetime, timezone
from unittest.mock import Mock
from django.test import TestCase
from faker import Faker
import pandas as pd
import numpy as np

from server.data_processors import FitzroyDataReader
from server.models import Match, TeamMatch, Team, MLModel, Prediction
from server.ml_models.betting_model import BettingModel, BettingModelData
from server.management.commands import seed_db

FAKE = Faker()
ROW_COUNT = 5
# Need real team names to match those in imported model data
TEAM_NAMES = [
    "Richmond",
    "Carlton",
    "Melbourne",
    "GWS",
    "Gold Coast",
    "Essendon",
    "Sydney",
    "Collingwood",
    "North Melbourne",
    "Adelaide",
    "Western Bulldogs",
    "Fremantle",
    "Port Adelaide",
    "St Kilda",
    "West Coast",
    "Brisbane",
    "Hawthorn",
    "Geelong",
]


class TestSeedDb(TestCase):
    def setUp(self):
        fixture_data = []
        self.years = (2015, 2017)

        for year in range(*self.years):
            match_date = datetime(year, 4, 1, tzinfo=timezone.utc)

            for _ in range(ROW_COUNT):
                fixture_data.append(
                    {
                        "date": pd.Timestamp(match_date),
                        "season": year,
                        "season_game": 1,
                        "round": 1,
                        "home_team": np.random.choice(TEAM_NAMES, 1)[0],
                        "away_team": np.random.choice(TEAM_NAMES, 1)[0],
                        "venue": FAKE.city(),
                    }
                )
        self.fixture_data_frame = pd.DataFrame(fixture_data)

        fitzroy = FitzroyDataReader()

        fitzroy.get_fixture = Mock(side_effect=self.__side_effect)

        estimator = BettingModel(name="betting_data")
        data_class = BettingModelData

        self.seed_command = seed_db.Command(
            data_reader=fitzroy, estimators=[(estimator, data_class)]
        )

    def test_handle(self):
        self.seed_command.handle(years="-".join([str(year) for year in self.years]))
        self.assertGreater(Team.objects.count(), 0)
        self.assertEqual(MLModel.objects.count(), 1)
        self.assertEqual(Match.objects.count(), ROW_COUNT * 2)
        self.assertEqual(TeamMatch.objects.count(), ROW_COUNT * 4)
        self.assertEqual(Prediction.objects.count(), ROW_COUNT * 2)

    def __side_effect(self, season=None):
        return self.fixture_data_frame[self.fixture_data_frame["season"] == season]
