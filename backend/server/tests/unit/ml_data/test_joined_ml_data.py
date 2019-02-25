from unittest import TestCase
from unittest.mock import Mock
import pandas as pd
import numpy as np
from faker import Faker

from server.ml_data import JoinedMLData


FAKE = Faker()
N_ROWS = 10


class TestJoinedMLData(TestCase):
    """Tests for JoinedMLData class"""

    def setUp(self):
        teams = [FAKE.company() for _ in range(N_ROWS)]
        years = ([2014] * 2) + ([2015] * 6) + ([2016] * 2)
        round_numbers = 15
        scores = np.random.randint(50, 150, N_ROWS)
        oppo_scores = np.random.randint(50, 150, N_ROWS)
        index_cols = ["team", "year", "round_number"]

        betting_data_reader = Mock()
        betting_data_reader().data = (
            pd.DataFrame(
                {
                    "team": teams,
                    "oppo_team": list(reversed(teams)),
                    "round_type": ["Regular"] * N_ROWS,
                    "year": years,
                    "score": scores,
                    "oppo_score": oppo_scores,
                    "round_number": round_numbers,
                    "win_odds": (np.random.rand(N_ROWS) * 2) + 1,
                    "oppo_win_odds": (np.random.rand(N_ROWS) * 2) + 1,
                }
            )
            .set_index(index_cols, drop=False)
            .rename_axis([None] * len(index_cols))
        )

        player_data_reader = Mock()
        player_data_reader().data = (
            pd.DataFrame(
                {
                    "team": teams,
                    "oppo_team": list(reversed(teams)),
                    "round_type": ["Regular"] * N_ROWS,
                    "year": years,
                    "score": scores,
                    "oppo_score": oppo_scores,
                    "round_number": round_numbers,
                    "kicks": np.random.randint(1, 20, N_ROWS),
                    "marks": np.random.randint(1, 20, N_ROWS),
                }
            )
            .set_index(index_cols, drop=False)
            .rename_axis([None] * len(index_cols))
        )

        match_data_reader = Mock()
        match_data_reader().data = (
            pd.DataFrame(
                {
                    "team": teams,
                    "oppo_team": list(reversed(teams)),
                    "round_type": ["Regular"] * N_ROWS,
                    "venue": [FAKE.city() for _ in range(N_ROWS)],
                    "year": years,
                    "score": scores,
                    "oppo_score": oppo_scores,
                    "round_number": round_numbers,
                    "rolling_win_percentage": np.random.rand(N_ROWS),
                    "ladder_position": np.random.randint(1, 18, N_ROWS),
                }
            )
            .set_index(index_cols, drop=False)
            .rename_axis([None] * len(index_cols))
        )

        self.data = JoinedMLData(
            data_readers=[betting_data_reader, player_data_reader, match_data_reader],
            data_transformers=[],
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
