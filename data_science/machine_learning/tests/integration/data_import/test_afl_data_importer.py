from unittest import TestCase
import pandas as pd

from machine_learning.data_import import AflDataImporter


class TestAflDataImporter(TestCase):
    def setUp(self):
        self.data_importer = AflDataImporter(verbose=0)

    def test_get_rosters(self):
        data_frame = self.data_importer.fetch_rosters(1)

        self.assertIsInstance(data_frame, pd.DataFrame)
