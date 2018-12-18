from unittest import TestCase
import pandas as pd
import numpy as np
from faker import Faker

from server.ml_models import BettingModel
from server.ml_models.betting_model import BettingModelData

FAKE = Faker()


class TestBettingModel(TestCase):
    def setUp(self):
        data_frame = pd.DataFrame(
            {
                "team": [FAKE.company() for _ in range(10)],
                "year": ([2014] * 2) + ([2015] * 6) + ([2016] * 2),
                "score": np.random.randint(50, 150, 10),
                "oppo_score": np.random.randint(50, 150, 10),
            }
        )
        self.X = pd.get_dummies(data_frame.drop("oppo_score", axis=1)).astype(float)
        self.y = data_frame["oppo_score"]
        self.model = BettingModel()

    def test_predict(self):
        self.model.fit(self.X, self.y)
        predictions = self.model.predict(self.X)

        self.assertIsInstance(predictions, pd.Series)


class TestBettingModelData(TestCase):
    def setUp(self):
        self.data_frame = pd.DataFrame(
            {
                "team": [FAKE.company() for _ in range(10)],
                "year": ([2014] * 2) + ([2015] * 6) + ([2016] * 2),
                "score": np.random.randint(50, 150, 10),
                "oppo_score": np.random.randint(50, 150, 10),
            }
        )
        self.data = BettingModelData(train_years=(2015, 2015), test_years=(2016, 2016))

    def test_train_data(self):
        X_train, y_train = self.data.train_data()

        self.assertIsInstance(X_train, pd.DataFrame)
        self.assertIsInstance(y_train, pd.Series)
        self.assertNotIn("score", X_train.columns)
        self.assertNotIn("oppo_score", X_train.columns)
        # No columns should be composed of strings
        self.assertFalse(
            any([X_train[column].dtype == "O" for column in X_train.columns])
        )
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
        # No columns should be composed of strings
        self.assertFalse(
            any([X_test[column].dtype == "O" for column in X_test.columns])
        )
        # Applying StandardScaler to integer columns raises a warning
        self.assertFalse(
            any([X_test[column].dtype == int for column in X_test.columns])
        )

    def test_train_test_data_compatibility(self):
        X_train, _ = self.data.train_data()
        X_test, _ = self.data.test_data()

        self.assertCountEqual(list(X_train.columns), list(X_test.columns))
