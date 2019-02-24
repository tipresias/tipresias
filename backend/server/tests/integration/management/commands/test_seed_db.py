import itertools
from datetime import datetime
from unittest.mock import Mock
from django.test import TestCase
from faker import Faker
import pandas as pd
from sklearn.externals import joblib

from server.data_readers import FootywireDataReader
from server.models import Match, TeamMatch, Team, MLModel, Prediction
from server.ml_data import BettingMLData
from server.management.commands import seed_db
from server.tests.fixtures import TestEstimator


FAKE = Faker()
ROW_COUNT = 5


class TestSeedDb(TestCase):
    def setUp(self):
        self.estimator = TestEstimator()
        self.data_class = BettingMLData

        joblib.dump = Mock()

        self.years = (2010, 2013)
        self.data = self.data_class().data

        # Mock footywire fixture data
        self.fixture_data_frame = self.__generate_fixture_data_frame(range(*self.years))

        footywire = FootywireDataReader()
        footywire.get_fixture = Mock(side_effect=self.__side_effect)

        self.seed_command = seed_db.Command(
            data_reader=footywire, estimators=[(self.estimator, self.data_class)]
        )

    def test_handle(self):
        self.seed_command.handle(
            year_range=f"{self.years[0]}-{self.years[1]}", verbose=0
        )

        self.assertGreater(Team.objects.count(), 0)
        self.assertEqual(MLModel.objects.count(), 1)
        self.assertEqual(Match.objects.count(), ROW_COUNT * len(range(*self.years)))
        self.assertEqual(
            TeamMatch.objects.count(), ROW_COUNT * len(range(*self.years)) * 2
        )
        # Should only have predictions for two years (2011 & 2012) due to betting data's
        # limitations (i.e. training data starts in 2010, so test data starts in 2011)
        self.assertEqual(
            Prediction.objects.count(), ROW_COUNT * (len(range(*self.years)) - 1)
        )

    def test_handle_errors(self):
        with self.subTest(
            "with invalid year_range argument due to it being a single year"
        ):
            with self.assertRaises(ValueError):
                self.seed_command.handle(year_range="2015", verbose=0)

        with self.subTest(
            "with invalid year_range argument due to years being separated by an invalid symbol"
        ):
            for symbol in [".", "_", ",", "/", "|"]:
                with self.assertRaises(ValueError):
                    self.seed_command.handle(
                        year_range=f"{self.years[0]}{symbol}{self.years[1]}", verbose=0
                    )

    def __side_effect(self, year_range=None):
        return self.fixture_data_frame[
            (self.fixture_data_frame["season"] >= year_range[0])
            & (self.fixture_data_frame["season"] < year_range[1])
        ]

    def __error_side_effect(self, error, year_range=None):
        error_season, error = error

        if year_range == error_season:
            raise error

        return self.__side_effect(year_range=year_range)

    def __generate_fixture_data_frame(self, year_range, valid=True):
        data = [self.__generate_year_data(year, valid=valid) for year in year_range]
        reduced_data = list(itertools.chain.from_iterable(data))

        return pd.DataFrame(list(reduced_data))

    def __generate_year_data(self, year, valid=True):
        if valid:
            # This guarantees that the mocked fixture data matches prediction data
            # so as not to raise errors or result in blank data frames
            sliced_data_frame = self.data.loc[
                (slice(None), year, 1), ["team", "at_home"]
            ]
            home_teams = sliced_data_frame[sliced_data_frame["at_home"] == 1]["team"]
            away_teams = sliced_data_frame[sliced_data_frame["at_home"] == 0]["team"]
        else:
            # Using GWS & University because they never played each other
            home_teams = pd.Series(["GWS"] * ROW_COUNT)
            away_teams = pd.Series(["University"] * ROW_COUNT)

        return [
            {
                "date": datetime(year, 4, 1, idx),
                "season": year,
                "round": 1,
                "round_label": "Round 1",
                "crowd": 1234,
                "home_team": home_teams.iloc[idx],
                "away_team": away_teams.iloc[idx],
                "home_score": 50,
                "away_score": 100,
                "venue": FAKE.city(),
            }
            for idx in range(ROW_COUNT)
        ]

    @staticmethod
    def __clear_db():
        Team.objects.all().delete()
        Match.objects.all().delete()
        MLModel.objects.all().delete()
