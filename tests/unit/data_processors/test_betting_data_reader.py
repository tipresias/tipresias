import os
import sys
from unittest import TestCase
import pandas as pd

project_path = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '../../../'))

if project_path not in sys.path:
    sys.path.append(project_path)

from app.data_processors import BettingDataReader


class TestBettingDataReader(TestCase):
    def setUp(self):
        self.reader = BettingDataReader()

    def test_transform(self):
        df = self.reader.transform('afl_betting.csv')

        self.assertIsInstance(df, pd.DataFrame)

        home_columns = df.columns[df.columns.str.match(r'home_')]
        away_columns = df.columns[df.columns.str.match(r'away_')]

        self.assertEqual(len(home_columns), len(away_columns))
