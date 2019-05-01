import itertools
from datetime import datetime
from unittest.mock import Mock, patch
from django.test import TestCase
from faker import Faker
import pandas as pd
from sklearn.externals import joblib

from server.models import Match, TeamMatch, Team, MLModel, Prediction
from server.management.commands import seed_db
from machine_learning.ml_data import BettingMLData
from machine_learning.tests.fixtures import TestEstimator


FAKE = Faker()
ROW_COUNT = 5


class TestSeedDb(TestCase):
    def setUp(self):
        joblib.dump = Mock()

        min_seed_year = int(seed_db.YEAR_RANGE.split("-")[0])
        # Min year needs to be greather than 2010, or weird stuff can happen
        # due to betting data only going back to 2010
        self.assertGreater(min_seed_year, 2010)

        # We only need a couple of valid years to test functionality
        self.years = (int(min_seed_year), int(min_seed_year + 2))
        # Need to add extra year at the beginning to provide at least one year's worth
        # of training data
        data_years = (self.years[0] - 1, self.years[1])
        self.data = BettingMLData().data

        # Mock footywire fixture data
        self.fixture_data_frame = self.__generate_fixture_data_frame(range(*data_years))
        self.betting_data_frame = self.__generate_betting_data_frame(range(*data_years))

        with patch(
            "machine_learning.ml_data.betting_ml_data.FootywireDataImporter"
        ) as MockDataReader:
            MockDataReader.return_value.get_fixture = Mock(
                side_effect=self.__fixture_side_effect
            )
            MockDataReader.return_value.get_betting_odds = Mock(
                side_effect=self.__betting_side_effect
            )

            self.seed_command = seed_db.Command(
                estimators=[TestEstimator()],
                data_reader=MockDataReader(),
                data=BettingMLData(),
            )

    def test_handle(self):
        with patch(
            "machine_learning.ml_data.betting_ml_data.FootywireDataImporter"
        ) as MockDataReader:
            MockDataReader.return_value.get_fixture = Mock(
                side_effect=self.__fixture_side_effect
            )
            MockDataReader.return_value.get_betting_odds = Mock(
                side_effect=self.__betting_side_effect
            )

            self.seed_command.handle(
                year_range=f"{self.years[0]}-{self.years[1]}", verbose=0
            )

        self.assertGreater(Team.objects.count(), 0)
        self.assertEqual(MLModel.objects.count(), 1)
        self.assertEqual(Match.objects.count(), ROW_COUNT * len(range(*self.years)))
        self.assertEqual(
            TeamMatch.objects.count(), ROW_COUNT * len(range(*self.years)) * 2
        )
        self.assertEqual(
            Prediction.objects.count(), ROW_COUNT * len(range(*self.years))
        )
        self.assertEqual(TeamMatch.objects.filter(score=0).count(), 0)

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

    def __fixture_side_effect(
        self, year_range=None, fetch_data=False
    ):  # pylint: disable=W0613
        if year_range is None:
            return self.fixture_data_frame

        return self.fixture_data_frame.query(
            "season >= @year_range[0] & season < @year_range[1]"
        )

    def __error_side_effect(self, error, year_range=None):
        error_season, error = error

        if year_range == error_season:
            raise error

        return self.__fixture_side_effect(year_range=year_range)

    def __betting_side_effect(
        self, year_range=None, fetch_data=False
    ):  # pylint: disable=W0613
        if year_range is None:
            return self.betting_data_frame

        return self.betting_data_frame.query(
            "season >= @year_range[0] & season < @year_range[1]"
        )

    def __generate_fixture_data_frame(self, year_range, valid=True):
        data = [
            self.__generate_fixture_year_data(year, valid=valid) for year in year_range
        ]
        reduced_data = list(itertools.chain.from_iterable(data))

        return pd.DataFrame(list(reduced_data))

    def __generate_fixture_year_data(self, year, valid=True):
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

    def __generate_betting_data_frame(self, year_range, valid=True):
        data = [
            self.__generate_betting_year_data(year, valid=valid) for year in year_range
        ]
        reduced_data = list(itertools.chain.from_iterable(data))

        return pd.DataFrame(list(reduced_data))

    def __generate_betting_year_data(self, year, valid=True):
        if valid:
            # This guarantees that the mocked betting data matches prediction data
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
                "round_label": f"{year} Round 1",
                "home_team": home_teams.iloc[idx],
                "away_team": away_teams.iloc[idx],
                "home_score": 50,
                "away_score": 100,
                "home_margin": 25,
                "away_margin": -25,
                "home_win_odds": 2,
                "away_win_odds": 1.2,
                "home_win_paid": 0,
                "away_win_paid": 1.2,
                "home_line_odds": 1.92,
                "away_line_odds": 1.92,
                "home_line_paid": 0,
                "away_line_paid": 1.92,
                "venue": FAKE.city(),
            }
            for idx in range(ROW_COUNT)
        ]

    @staticmethod
    def __clear_db():
        Team.objects.all().delete()
        Match.objects.all().delete()
        MLModel.objects.all().delete()
