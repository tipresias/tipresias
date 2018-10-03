import os
import sys
from unittest import TestCase
import pandas as pd
import numpy as np
from faker import Faker

PROJECT_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '../../')
)

if PROJECT_PATH not in sys.path:
    sys.path.append(PROJECT_PATH)

from server.ml_models import BettingLasso
from server.ml_models.betting_lasso import BettingLassoData

FAKE = Faker()


class TestBettingLasso(TestCase):
    def setUp(self):
        data_frame = pd.DataFrame({
            'team': [FAKE.company() for _ in range(10)],
            'year': ([2014] * 2) + ([2015] * 6) + ([2016] * 2),
            'score': np.random.randint(50, 150, 10),
            'oppo_score': np.random.randint(50, 150, 10)
        })
        self.X = pd.get_dummies(data_frame.drop('oppo_score', axis=1))
        self.y = data_frame['oppo_score']
        self.model = BettingLasso()

    def test_predict(self):
        self.model.fit(self.X, self.y)
        predictions = self.model.predict(self.X)

        self.assertIsInstance(predictions, pd.DataFrame)


class TestBettingLassoData(TestCase):
    def setUp(self):
        self.data_frame = pd.DataFrame({
            'team': [FAKE.company() for _ in range(10)],
            'year': ([2014] * 2) + ([2015] * 6) + ([2016] * 2),
            'score': np.random.randint(50, 150, 10),
            'oppo_score': np.random.randint(50, 150, 10)
        })
        self.data = BettingLassoData()

    def test_training_data(self):
        X_train, y_train = self.data.training_data()

        self.assertIsInstance(X_train, pd.DataFrame)
        self.assertIsInstance(y_train, pd.Series)
        self.assertNotIn('score', X_train.columns)
        self.assertNotIn('oppo_score', X_train.columns)
        # No columns should be composed of strings
        self.assertFalse(
            any([X_train[column].dtype == 'O' for column in X_train.columns])
        )
