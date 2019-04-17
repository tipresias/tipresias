from unittest import TestCase
import pandas as pd
import numpy as np
from sklearn.linear_model import Ridge, Lasso
from sklearn.pipeline import make_pipeline
from sklearn.externals import joblib
from faker import Faker

from machine_learning.ml_estimators import BaggingEstimator
from machine_learning.ml_estimators.sklearn import AveragingRegressor

FAKE = Faker()
N_ROWS = 10


class TestBaggingEstimator(TestCase):
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
        self.X = pd.get_dummies(
            data_frame.drop(["score", "oppo_score"], axis=1)
        ).astype(float)
        self.y = data_frame["score"] - data_frame["oppo_score"]
        pipeline = make_pipeline(
            AveragingRegressor([("ridge", Ridge()), ("lasso", Lasso())])
        )
        self.model = BaggingEstimator(pipeline=pipeline, name="tipresias")

    def test_predict(self):
        self.model.fit(self.X, self.y)
        predictions = self.model.predict(self.X)

        self.assertIsInstance(predictions, np.ndarray)

    def test_pickle_file_compatibility(self):
        loaded_model = joblib.load(self.model.pickle_filepath())
        self.assertIsInstance(loaded_model, BaggingEstimator)
