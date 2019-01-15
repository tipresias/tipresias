from unittest import TestCase
from unittest.mock import Mock
import pandas as pd
import numpy as np
from sklearn.linear_model import Ridge
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder
from sklearn.pipeline import make_pipeline
from faker import Faker

from project.settings.common import BASE_DIR
from server.ml_models import AllModel
from server.ml_models.all_model import AllModelData

FAKE = Faker()
N_ROWS = 10

get_afltables_stats_df = pd.read_csv(
    f"{BASE_DIR}/server/tests/fixtures/fitzroy_get_afltables_stats.csv"
)
match_results_df = pd.read_csv(
    f"{BASE_DIR}/server/tests/fixtures/fitzroy_match_results.csv"
)
get_afltables_stats_mock = Mock(return_value=get_afltables_stats_df)
match_results_mock = Mock(return_value=match_results_df)


class TestAllModel(TestCase):
    def setUp(self):
        data_frame = pd.DataFrame(
            {
                "team": [FAKE.company() for _ in range(10)],
                "year": ([2014] * 2) + ([2015] * 6) + ([2016] * 2),
                "score": np.random.randint(50, 150, 10),
                "oppo_score": np.random.randint(50, 150, 10),
                "round_number": 15,
            }
        )
        self.X = data_frame.drop("oppo_score", axis=1)
        self.y = data_frame["oppo_score"]
        pipeline = make_pipeline(
            ColumnTransformer(
                [("onehot", OneHotEncoder(sparse=False), ["team"])],
                remainder="passthrough",
            ),
            Ridge(),
        )
        self.model = AllModel(pipeline=pipeline)

    def test_predict(self):
        self.model.fit(self.X, self.y)
        predictions = self.model.predict(self.X)

        self.assertIsInstance(predictions, np.ndarray)


class TestAllModelData(TestCase):
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

        self.data = AllModelData(
            data_readers=[betting_data_reader, player_data_reader, match_data_reader]
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
