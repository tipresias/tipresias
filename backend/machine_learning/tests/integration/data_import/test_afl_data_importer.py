from unittest import skip
from django.test import TestCase
import pandas as pd

from machine_learning.data_import import AflDataImporter


@skip("I'll need to set up afl_data in CI to get these importer tests working")
class TestAflDataImporter(TestCase):
    def setUp(self):
        self.data_importer = AflDataImporter()

    def test_get_rosters(self):
        data_frame = self.data_importer.fetch_rosters(1)

        self.assertIsInstance(data_frame, pd.DataFrame)
