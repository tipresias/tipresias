# TODO: After refactoring, mock the bejeezus out of this test with a basic linear
# model and fake data, because this is getting closer to an integration test with
# each import

import copy
import os
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock
from django.test import TestCase
from faker import Faker
from freezegun import freeze_time
import pandas as pd

from project.settings.common import BASE_DIR
from server.data_processors import FitzroyDataReader
from server.models import Match, TeamMatch, Team, MLModel, Prediction
from server.management.commands import tip
from server.ml_models.betting_model import BettingModel, BettingModelData

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

# Freezing time to make sure there is viable data, which is easier
# than mocking viable data
@freeze_time("2016-01-01")
class TestTip(TestCase):
    def setUp(self):
        tomorrow = datetime.now(timezone.utc) + timedelta(days=1)
        year = tomorrow.year
        team_names = TEAM_NAMES[:]

        # Mock fitzRoy fixture data
        self.fixture_data = [
            {
                "date": pd.Timestamp(tomorrow),
                "season": year,
                "season_game": 1,
                "round": 1,
                "home_team": team_names.pop(),
                "away_team": team_names.pop(),
                "venue": FAKE.city(),
            }
            for idx in range(ROW_COUNT)
        ]

        fitzroy = FitzroyDataReader()
        fitzroy.get_fixture = Mock(return_value=pd.DataFrame(self.fixture_data))

        # Mock bulk_create to make assertions on calls
        pred_bulk_create = copy.copy(Prediction.objects.bulk_create)
        Prediction.objects.bulk_create = Mock(
            side_effect=self.__pred_bulk_create(pred_bulk_create)
        )

        # Save records in DB
        for match_data in self.fixture_data:
            Team(name=match_data["home_team"]).save()
            Team(name=match_data["away_team"]).save()

        betting_model = BettingModel(name="betting_data")

        pickle_filepath = os.path.abspath(
            os.path.join(BASE_DIR, "server", "tests", "fixtures", "betting_data.pkl")
        )
        MLModel(
            name=betting_model.name,
            description="Betting data model",
            filepath=pickle_filepath,
            data_class_path=BettingModelData.class_path(),
        ).save()

        self.tip_command = tip.Command(data_reader=fitzroy)

    def test_handle(self):
        with self.subTest("with no existing match records in DB"):
            self.assertEqual(Match.objects.count(), 0)
            self.assertEqual(TeamMatch.objects.count(), 0)
            self.assertEqual(Prediction.objects.count(), 0)

            self.tip_command.handle(verbose=0)

            self.assertEqual(Match.objects.count(), ROW_COUNT)
            self.assertEqual(TeamMatch.objects.count(), ROW_COUNT * 2)
            self.assertEqual(Prediction.objects.count(), ROW_COUNT)

        with self.subTest("with the match records already saved in the DB"):
            self.assertEqual(Match.objects.count(), ROW_COUNT)
            self.assertEqual(TeamMatch.objects.count(), ROW_COUNT * 2)
            self.assertEqual(Prediction.objects.count(), ROW_COUNT)

            self.tip_command.handle(verbose=0)

            Prediction.objects.bulk_create.assert_called()

    @staticmethod
    def __pred_bulk_create(pred_bulk_create):
        return pred_bulk_create
