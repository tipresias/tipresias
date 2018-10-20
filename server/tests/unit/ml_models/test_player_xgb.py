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

from server.ml_models import PlayerXGB
from server.ml_models.player_xgb import PlayerXGBData

FAKE = Faker()


class TestPlayerXGB(TestCase):
    def setUp(self):
        data_frame = pd.DataFrame({
            'team': [FAKE.company() for _ in range(10)],
            'year': ([2014] * 2) + ([2015] * 6) + ([2016] * 2),
            'score': np.random.randint(50, 150, 10),
            'oppo_score': np.random.randint(50, 150, 10),
            'round_number': 15
        })
        self.X = (pd
                  .get_dummies(data_frame.drop('oppo_score', axis=1))
                  .astype(float))
        self.y = data_frame['oppo_score']
        self.model = PlayerXGB()

    def test_predict(self):
        self.model.fit(self.X, self.y)
        predictions = self.model.predict(self.X)

        self.assertIsInstance(predictions, pd.Series)


class TestPlayerXGBData(TestCase):
    def setUp(self):
        self.data = PlayerXGBData(start_date='2015-01-01')

    def test_train_data(self):
        X_train, y_train = self.data.train_data()

        self.assertIsInstance(X_train, pd.DataFrame)
        self.assertIsInstance(y_train, pd.Series)
        self.assertNotIn('score', X_train.columns)
        self.assertNotIn('oppo_score', X_train.columns)
        self.assertNotIn('goals', X_train.columns)
        self.assertNotIn('oppo_goals', X_train.columns)
        self.assertNotIn('behinds', X_train.columns)
        self.assertNotIn('oppo_behinds', X_train.columns)
        # No columns should be composed of strings
        self.assertFalse(
            any([X_train[column].dtype == 'O' for column in X_train.columns])
        )
        # Applying StandardScaler to integer columns raises a warning
        self.assertFalse(
            any([X_train[column].dtype == int for column in X_train.columns])
        )

    def test_test_data(self):
        X_test, y_test = self.data.test_data()

        self.assertIsInstance(X_test, pd.DataFrame)
        self.assertIsInstance(y_test, pd.Series)
        self.assertNotIn('score', X_test.columns)
        self.assertNotIn('oppo_score', X_test.columns)
        self.assertNotIn('goals', X_test.columns)
        self.assertNotIn('oppo_goals', X_test.columns)
        self.assertNotIn('behinds', X_test.columns)
        self.assertNotIn('oppo_behinds', X_test.columns)
        # No columns should be composed of strings
        self.assertFalse(
            any([X_test[column].dtype == 'O' for column in X_test.columns])
        )
        # Applying StandardScaler to integer columns raises a warning
        self.assertFalse(
            any([X_test[column].dtype == int for column in X_test.columns])
        )

    def test_train_test_data_compatibility(self):
        self.maxDiff = None

        X_train, _ = self.data.train_data()
        X_test, _ = self.data.test_data()

        self.assertCountEqual(list(X_train.columns), list(X_test.columns))
