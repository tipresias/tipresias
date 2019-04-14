import os
from unittest import TestCase
from unittest.mock import Mock
import pandas as pd
import numpy as np
from faker import Faker

from machine_learning.ml_data import JoinedMLData

DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../fixtures"))
FAKE = Faker()
N_ROWS = 10


class TestJoinedMLData(TestCase):
    """Tests for JoinedMLData class"""

    def setUp(self):
        betting_data_reader = Mock(
            return_value=pd.read_csv(os.path.join(DATA_DIR, "afl_betting.csv"))
        )

        player_data_reader = Mock(
            return_value=pd.read_csv(
                os.path.join(DATA_DIR, "fitzroy_get_afltables_stats.csv")
            )
        )

        match_data_reader = Mock(
            return_value=pd.read_csv(
                os.path.join(DATA_DIR, "fitzroy_match_results.csv")
            )
        )

        self.data = JoinedMLData(
            data_readers={
                "betting": (betting_data_reader, {}),
                "player": (player_data_reader, {}),
                "match": (match_data_reader, {}),
            },
            data_transformers=[self.__set_valid_index, self.__assign_score_cols],
            category_cols=None,
            train_years=(None, 2016),
        )

    def test_train_data(self):
        X_train, y_train = self.data.train_data()

        self.assertIsInstance(X_train, pd.DataFrame)
        self.assertIsInstance(y_train, pd.Series)
        self.assertNotIn("score", X_train.columns)
        self.assertNotIn("oppo_score", X_train.columns)

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
        return data_frame.set_index(["home_team", "year", "round_number"])

    @staticmethod
    def __assign_score_cols(data_frame):
        return data_frame.assign(
            score=data_frame["home_score"], oppo_score=data_frame["away_score"]
        )

