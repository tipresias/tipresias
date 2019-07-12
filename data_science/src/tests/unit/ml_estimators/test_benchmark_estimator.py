from unittest import TestCase
from unittest.mock import Mock
import os
import pandas as pd
import numpy as np
from sklearn.linear_model import Ridge
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder
from sklearn.pipeline import make_pipeline
from sklearn.externals import joblib
from faker import Faker

from machine_learning.settings import BASE_DIR
from machine_learning.ml_estimators import BenchmarkEstimator

FAKE = Faker()
N_ROWS = 10

get_afltables_stats_df = pd.read_csv(
    os.path.join(BASE_DIR, "src/tests/fixtures/fitzroy_get_afltables_stats.csv")
)
match_results_df = pd.read_csv(
    os.path.join(BASE_DIR, "src/tests/fixtures/fitzroy_match_results.csv")
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
                [
                    (
                        "onehot",
                        OneHotEncoder(sparse=False, handle_unknown="ignore"),
                        ["team"],
                    )
                ],
                remainder="passthrough",
            ),
            Ridge(),
        )
        self.model = BenchmarkEstimator(pipeline=pipeline, name="benchmark_estimator")

    def test_predict(self):
        self.model.fit(self.X, self.y)
        predictions = self.model.predict(self.X)

        self.assertIsInstance(predictions, np.ndarray)

    def test_pickle_file_compatibility(self):
        loaded_model = joblib.load(self.model.pickle_filepath())
        self.assertIsInstance(loaded_model, BenchmarkEstimator)
