import os
import sys
from unittest import TestCase
import pandas as pd

PROJECT_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '../../../'))

if PROJECT_PATH not in sys.path:
    sys.path.append(PROJECT_PATH)

from app.data_processors import BettingDataReader


class TestBettingDataReader(TestCase):
    def setUp(self):
        self.reader = BettingDataReader()

    def test_transform(self):
        data_frame = self.reader.transform('afl_betting.csv')

        self.assertIsInstance(data_frame, pd.DataFrame)

        home_columns = data_frame.columns[data_frame.columns.str.match(
            r'home_')]
        away_columns = data_frame.columns[data_frame.columns.str.match(
            r'away_')]

        self.assertEqual(len(home_columns), len(away_columns))
