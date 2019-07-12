import os
import warnings
from unittest import TestCase
from unittest.mock import Mock
import pandas as pd
from faker import Faker

from machine_learning.ml_data import JoinedMLData
from machine_learning.data_transformation import data_cleaning
from tests.fixtures.data_factories import fake_cleaned_match_data

DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../fixtures"))
FAKE = Faker()
MATCH_COUNT_PER_YEAR = 10
YEAR_RANGE = (2016, 2017)
# Need to multiply by two, because we add team & oppo_team row per match
ROW_COUNT = MATCH_COUNT_PER_YEAR * len(range(*YEAR_RANGE)) * 2

# JoinedMLData does a .loc call with all the column names, resulting in a
# warning about passing missing column names to .loc when we run tests, so
# we're ignoring the warnings rather than adding all the columns
warnings.simplefilter("ignore", FutureWarning)


class TestJoinedMLData(TestCase):
    """Tests for JoinedMLData class"""

    def setUp(self):
        base_data = fake_cleaned_match_data(MATCH_COUNT_PER_YEAR, YEAR_RANGE)

        betting_data_reader = Mock()
        betting_data_reader.data = base_data.assign(line_odds=20, oppo_line_odds=-20)

        player_data_reader = Mock()
        player_data_reader.data = base_data.assign(
            rolling_kicks=50, oppo_rolling_kicks=75
        )

        match_data_reader = Mock()
        match_data_reader.data = base_data.assign(
            ladder_position=2, oppo_ladder_position=6
        )

        self.data = JoinedMLData(
            data_readers={
                "betting": betting_data_reader,
                "player": player_data_reader,
                "match": match_data_reader,
            },
            data_transformers=[data_cleaning.clean_joined_data, self.__set_valid_index],
            category_cols=None,
            train_years=(None, 2016),
        )

    def test_train_data(self):
        X_train, y_train = self.data.train_data()

        self.assertIsInstance(X_train, pd.DataFrame)
        self.assertIsInstance(y_train, pd.Series)
        self.assertNotIn("score", X_train.columns)
        self.assertNotIn("oppo_score", X_train.columns)
        self.assertNotIn("goals", X_train.columns)
        self.assertNotIn("team_goals", X_train.columns)
        self.assertNotIn("oppo_team_goals", X_train.columns)
        self.assertNotIn("behinds", X_train.columns)
        self.assertNotIn("team_behinds", X_train.columns)
        self.assertNotIn("oppo_team_behinds", X_train.columns)
        self.assertNotIn("margin", X_train.columns)
        self.assertNotIn("result", X_train.columns)

        # Applying StandardScaler to integer columns raises a warning
        self.assertFalse(
            any([X_train[column].dtype == int for column in X_train.columns])
        )

    def test_test_data(self):
        X_test, y_test = self.data.test_data()

        self.assertIsInstance(X_test, pd.DataFrame)
        self.assertIsInstance(y_test, pd.Series)
        self.assertNotIn("score", X_test.columns)
        self.assertNotIn("oppo_score", X_test.columns)
        self.assertNotIn("goals", X_test.columns)
        self.assertNotIn("team_goals", X_test.columns)
        self.assertNotIn("oppo_team_goals", X_test.columns)
        self.assertNotIn("behinds", X_test.columns)
        self.assertNotIn("team_behinds", X_test.columns)
        self.assertNotIn("oppo_team_behinds", X_test.columns)
        self.assertNotIn("margin", X_test.columns)
        self.assertNotIn("result", X_test.columns)

        # Applying StandardScaler to integer columns raises a warning
        self.assertFalse(
            any([X_test[column].dtype == int for column in X_test.columns])
        )

    def test_train_test_data_compatibility(self):
        self.maxDiff = None

        X_train, _ = self.data.train_data()
        X_test, _ = self.data.test_data()

        self.assertCountEqual(list(X_train.columns), list(X_test.columns))

    @staticmethod
    def __set_valid_index(data_frame):
        return data_frame.set_index(["team", "year", "round_number"])
