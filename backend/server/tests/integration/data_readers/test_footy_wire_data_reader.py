import os
from django.test import TestCase
import pandas as pd

from server.data_readers import FootywireDataReader

DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../fixtures"))


class TestFootywireDataReader(TestCase):
    def setUp(self):
        self.data_reader = FootywireDataReader(csv_dir=DATA_DIR)

    def test_get_fixture(self):
        with self.subTest("when fresh_data is True"):
            data_frame = self.data_reader.get_fixture(
                year_range=(2014, 2015), fresh_data=True
            )

            self.assertIsInstance(data_frame, pd.DataFrame)

            seasons = data_frame["season"].drop_duplicates()
            self.assertEqual(len(seasons), 1)
            self.assertEqual(seasons.iloc[0], 2014)

            date_years = data_frame["date"].dt.year.drop_duplicates()
            self.assertEqual(len(date_years), 1)
            self.assertEqual(date_years.iloc[0], 2014)

        with self.subTest("when fresh_data is False"):
            data_frame = self.data_reader.get_fixture(fresh_data=False)

            self.assertIsInstance(data_frame, pd.DataFrame)
            self.assertFalse(data_frame.empty)

        with self.subTest("when fresh_data is False and year_range is specified"):
            data_frame = self.data_reader.get_fixture(
                fresh_data=False, year_range=(2018, 2019)
            )

            self.assertIsInstance(data_frame, pd.DataFrame)
            seasons = data_frame["season"].drop_duplicates()
            self.assertEqual(len(seasons), 1)
            self.assertEqual(seasons.iloc[0], 2018)

    def test_get_betting_odds(self):
        with self.subTest("when fresh_data is True"):
            data_frame = self.data_reader.get_betting_odds(
                year_range=(2014, 2015), fresh_data=True
            )

            self.assertIsInstance(data_frame, pd.DataFrame)

            seasons = data_frame["season"].drop_duplicates()
            self.assertEqual(len(seasons), 1)
            self.assertEqual(seasons.iloc[0], 2014)

            date_years = data_frame["date"].dt.year.drop_duplicates()
            self.assertEqual(len(date_years), 1)
            self.assertEqual(date_years.iloc[0], 2014)

        with self.subTest("when fresh_data is False"):
            data_frame = self.data_reader.get_betting_odds(fresh_data=False)

            self.assertIsInstance(data_frame, pd.DataFrame)
            self.assertFalse(data_frame.empty)

        with self.subTest("when fresh_data is False and year_range is specified"):
            data_frame = self.data_reader.get_betting_odds(
                fresh_data=False, year_range=(2018, 2019)
            )

            self.assertIsInstance(data_frame, pd.DataFrame)
            seasons = data_frame["season"].drop_duplicates()
            self.assertEqual(len(seasons), 1)
            self.assertEqual(seasons.iloc[0], 2018)
