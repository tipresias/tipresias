import os
import sys
from unittest import TestCase
import pandas as pd
import numpy as np
from faker import Faker

PROJECT_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '../../../'))

if PROJECT_PATH not in sys.path:
    sys.path.append(PROJECT_PATH)

from app.data_processors import DataCleaner

np.random.seed(42)

FAKE = Faker()


class TestDataCleaner(TestCase):
    def setUp(self):
        # DataFrame w/ minimum valid columns
        self.data_frame = pd.DataFrame({
            'venue': [FAKE.city() for _ in range(10)],
            'crowd': [np.random.randint(10000, high=40000) for _ in range(10)],
            'datetime': [FAKE.date_time_this_century() for _ in range(10)],
            'season_round': [f'round {np.random.randint(1, 24)}' for _ in range(10)]
        })
        self.array = self.data_frame.values
        self.invalid_df = self.data_frame.drop('venue', axis=1)
        self.cleaner = DataCleaner(drop_cols=['venue', 'crowd'])

    def test_transform(self):
        with self.subTest(data_frame=self.data_frame):
            data_frame = self.cleaner.transform(self.data_frame)

            self.assertTrue(
                all((col in data_frame.columns for col in [
                    'round_number', 'year']))
            )
            self.assertFalse(
                any((col in data_frame.columns for col in
                     ['datetime', 'season_round', 'venue', 'crowd']))
            )

        with self.subTest(data_frame=self.array):
            with self.assertRaises(TypeError):
                self.cleaner.transform(self.array)

        with self.subTest(data_frame=self.invalid_df):
            with self.assertRaises(ValueError):
                self.cleaner.transform(self.invalid_df)
