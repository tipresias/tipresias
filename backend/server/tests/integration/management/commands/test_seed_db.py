# TODO: After refactoring, mock the bejeezus out of this test with a basic linear
# model and fake data, because this is getting closer to an integration test with
# each import

from functools import reduce
from datetime import datetime
from unittest.mock import Mock
from django.test import TestCase
from faker import Faker
import pandas as pd

from server.data_readers import FootywireDataReader
from server.models import Match, TeamMatch, Team, MLModel, Prediction
from server.ml_models.betting_model import BettingModel, BettingModelData
from server.management.commands import seed_db

FAKE = Faker()
ROW_COUNT = 5


class TestSeedDb(TestCase):
    def setUp(self):
        estimator = BettingModel(name="betting_data")
        data_class = BettingModelData

        self.years = (2010, 2013)
        self.data = data_class().data

        # Mock footywire fixture data
        self.fixture_data_frame = self.__generate_fixture_data_frame(range(*self.years))

        footywire = FootywireDataReader()
        footywire.get_fixture = Mock(side_effect=self.__side_effect)

        self.seed_command = seed_db.Command(
            data_reader=footywire, estimators=[(estimator, data_class)]
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
        reduced_data = reduce(lambda acc_list, curr_list: acc_list + curr_list, data)

        return pd.DataFrame(reduced_data)

    def __generate_year_data(self, year, valid=True):
        if valid:
            # This guarantees that the mocked fixture data matches prediction data
            # so as not to raise errors or result in blank data frames
            sliced_data_frame = self.data.loc[
                (slice(None), year, 1), ["team", "at_home"]
            ]
            home_team = sliced_data_frame[sliced_data_frame["at_home"] == 1][
                "team"
            ].iloc[0]
            away_team = sliced_data_frame[sliced_data_frame["at_home"] == 0][
                "team"
            ].iloc[0]
        else:
            # Using GWS & University because they never played each other
            home_team = "GWS"
            away_team = "University"

        return [
            {
                "date": datetime(year, 4, 1, idx),
                "season": year,
                "round": 1,
                "round_label": "Round 1",
                "crows": 1234,
                "home_team": home_team,
                "away_team": away_team,
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
