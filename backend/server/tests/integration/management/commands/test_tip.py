import copy
from datetime import datetime, timedelta
from unittest.mock import Mock
from django.test import TestCase
from faker import Faker
from freezegun import freeze_time
import pandas as pd

from server.data_readers import FootywireDataReader
from server.models import Match, TeamMatch, Team, MLModel, Prediction
from server.management.commands import tip
from server.ml_data import BettingMLData
from server.tests.fixtures import TestEstimator

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
        tomorrow = datetime.now() + timedelta(days=1)
        year = tomorrow.year
        team_names = TEAM_NAMES[:]

        # Mock footywire fixture data
        self.fixture_data = [
            {
                "date": tomorrow,
                "season": year,
                "round": 1,
                "round_label": "Round 1",
                "crows": 1234,
                "home_team": team_names.pop(),
                "away_team": team_names.pop(),
                "home_score": 50,
                "away_score": 100,
                "venue": FAKE.city(),
            }
            for idx in range(ROW_COUNT)
        ]

        footywire = FootywireDataReader()
        footywire.get_fixture = Mock(return_value=pd.DataFrame(self.fixture_data))

        # Mock bulk_create to make assertions on calls
        pred_bulk_create = copy.copy(Prediction.objects.bulk_create)
        Prediction.objects.bulk_create = Mock(
            side_effect=self.__pred_bulk_create(pred_bulk_create)
        )

        # Save records in DB
        for match_data in self.fixture_data:
            Team(name=match_data["home_team"]).save()
            Team(name=match_data["away_team"]).save()

        test_estimator = TestEstimator()

        MLModel(
            name=test_estimator.name,
            description="Test estimator model",
            filepath=test_estimator.pickle_filepath(),
            data_class_path=BettingMLData.class_path(),
        ).save()

        # Not fetching data, because it takes forever
        self.tip_command = tip.Command(data_reader=footywire, fetch_data=False)

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

            self.assertEqual(Match.objects.count(), ROW_COUNT)
            self.assertEqual(TeamMatch.objects.count(), ROW_COUNT * 2)

    @staticmethod
    def __pred_bulk_create(pred_bulk_create):
        return pred_bulk_create
