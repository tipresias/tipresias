# TODO: After refactoring, mock the bejeezus out of this test with a basic linear
# model and fake data, because this is getting closer to an integration test with
# each import

from functools import reduce, partial
from datetime import datetime, timezone
from unittest.mock import Mock
from django.test import TestCase
from faker import Faker
import pandas as pd

from server.data_readers import FitzroyDataReader
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

        # Mock fitzRoy fixture data
        self.fixture_data_frame = self.__generate_fixture_data_frame(range(*self.years))

        fitzroy = FitzroyDataReader()
        fitzroy.get_fixture = Mock(side_effect=self.__side_effect)

        self.seed_command = seed_db.Command(
            data_reader=fitzroy, estimators=[(estimator, data_class)]
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

        with self.subTest("when FitzroyDataReader raises a RuntimError"):
            side_effect = partial(
                self.__error_side_effect, (self.years[0], RuntimeError)
            )
            self.seed_command.data_reader.get_fixture = Mock(side_effect=side_effect)

            self.assertIsNone(
                self.seed_command.handle(f"{self.years[0]}-{self.years[1]}", verbose=0)
            )

        self.__clear_db()

        with self.subTest(
            "when FitzroyDataReader raises a ValueError and the requested season is 2015"
        ):
            side_effect = partial(self.__error_side_effect, (2015, ValueError))
            self.seed_command.data_reader.get_fixture = Mock(side_effect=side_effect)

            self.assertIsNone(
                self.seed_command.handle(
                    year_range=f"{self.years[0]}-{self.years[1]}", verbose=0
                )
            )

        self.__clear_db()

        with self.subTest(
            "when FitzroyDataReader raises a ValueError and the requested year is not 2015"
        ):
            side_effect = partial(self.__error_side_effect, (2012, ValueError))
            self.seed_command.data_reader.get_fixture = Mock(side_effect=side_effect)

            with self.assertRaises(ValueError):
                self.seed_command.handle(
                    year_range=f"{self.years[0]}-{self.years[1]}", verbose=0
                )

    def test_handle_bad_data(self):
        with self.subTest("when the requested season is known to have bad data"):
            self.fixture_data_frame = self.fixture_data_frame.append(
                self.__generate_fixture_data_frame(seed_db.DODGY_SEASONS, valid=False)
            )

            for season in seed_db.DODGY_SEASONS:
                # handle will raise ValueError for empty data frame, but not the
                # KeyError that would be the natural result of the mismatched data
                with self.assertRaises(ValueError):
                    self.seed_command.handle(
                        year_range=f"{season}-{season + 1}", verbose=0
                    )

        self.__clear_db()

        with self.subTest("when the requested season is supposedly correct"):
            season = 2011
            self.assertNotIn(season, seed_db.DODGY_SEASONS)

            self.fixture_data_frame = self.fixture_data_frame.append(
                self.__generate_fixture_data_frame([season], valid=False)
            )

            with self.assertRaises(KeyError):
                self.seed_command.handle(year_range=f"{season}-{season + 1}", verbose=0)

    def __side_effect(self, season=None):
        return self.fixture_data_frame[self.fixture_data_frame["season"] == season]

    def __error_side_effect(self, error, season=None):
        error_season, error = error

        if season == error_season:
            raise error

        return self.__side_effect(season=season)

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
                "date": datetime(year, 4, 1, idx, tzinfo=timezone.utc),
                "season": year,
                "season_game": 1,
                "round": 1,
                "home_team": home_team,
                "away_team": away_team,
                "venue": FAKE.city(),
            }
            for idx in range(ROW_COUNT)
        ]

    @staticmethod
    def __clear_db():
        Team.objects.all().delete()
        Match.objects.all().delete()
        MLModel.objects.all().delete()
