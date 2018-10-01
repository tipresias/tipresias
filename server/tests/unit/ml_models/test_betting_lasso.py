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

FAKE = Faker()


class TestBettingLasso(TestCase):
    def setUp(self):
        self.data_frame = pd.DataFrame({
            'team': [FAKE.company() for _ in range(10)],
            'year': ([2014] * 2) + ([2015] * 6) + ([2016] * 2),
            'score': np.random.randint(50, 150, 10),
            'oppo_score': np.random.randint(50, 150, 10)
        })
        self.model = BettingLasso()

    def test_predict(self):
        self.model.fit(min_year=2016, max_year=2016)
        predictions = self.model.predict(min_year=2016, max_year=2016)

        self.assertIsInstance(predictions, pd.DataFrame)
        self.assertEqual(len(predictions), 2)
