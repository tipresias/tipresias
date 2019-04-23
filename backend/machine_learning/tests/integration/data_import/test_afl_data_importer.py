from django.test import TestCase
import pandas as pd

from machine_learning.data_import import afl_data_importer


class TestAflDataImporter(TestCase):
    def setUp(self):
        self.data_importer = afl_data_importer

    def test_get_rosters(self):
        data_frame = self.data_importer.get_rosters(1)

        self.assertIsInstance(data_frame, pd.DataFrame)
