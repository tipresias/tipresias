import os
from unittest import TestCase
import pandas as pd

from machine_learning.data_transformation.data_cleaning import clean_betting_data

DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../fixtures"))


class TestDataCleaning(TestCase):
    def test_clean_betting_data(self):
        betting_data = pd.read_csv(os.path.join(DATA_DIR, "afl_betting.csv"))
        match_data = pd.read_csv(os.path.join(DATA_DIR, "ft_match_list.csv"))

        clean_data = clean_betting_data(betting_data, match_data)

        self.assertIsInstance(clean_data, pd.DataFrame)

        required_columns = ["home_team", "away_team", "year", "round_number"]

        for col in required_columns:
            self.assertTrue(col in clean_data.columns.values)
