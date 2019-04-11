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
from server.ml_estimators import BenchmarkEstimator

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


class TestBenchmarkEstimator(TestCase):
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
        self.model = BenchmarkEstimator(pipeline=pipeline)

    def test_predict(self):
        self.model.fit(self.X, self.y)
        predictions = self.model.predict(self.X)

        self.assertIsInstance(predictions, np.ndarray)
