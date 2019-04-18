from django.test import TestCase
import pandas as pd

from machine_learning.data_import import afl_data_importer


class TestAflDataReader(TestCase):
    def setUp(self):
        self.data_reader = afl_data_importer

    def test_get_rosters(self):
        data_frame = self.data_reader.get_rosters()

        self.assertIsInstance(data_frame, pd.DataFrame)
