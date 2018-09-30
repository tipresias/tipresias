import os
import sys
from unittest import TestCase
import pandas as pd

PROJECT_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '../../../'))

if PROJECT_PATH not in sys.path:
    sys.path.append(PROJECT_PATH)

from server.data_processors import MatchDataReader


class TestMatchDataReader(TestCase):
    def setUp(self):
        self.reader = MatchDataReader()

    def test_transform(self):
        data_frame = self.reader.transform('ft_match_list.csv')

        self.assertIsInstance(data_frame, pd.DataFrame)

        home_columns = (
            data_frame.columns[data_frame.columns.str.match(r'home_')]
        )
        away_columns = (
            data_frame.columns[data_frame.columns.str.match(r'away_')]
        )

        self.assertEqual(len(home_columns), len(away_columns))
