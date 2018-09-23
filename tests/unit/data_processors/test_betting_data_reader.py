import os
import sys
from unittest import TestCase

project_path = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '../../../'))

if project_path not in sys.path:
    sys.path.append(project_path)

from app.data_processors import BettingDataReader


class TestBettingDataReader(TestCase):
    def setUp(self):
        self.described_class = BettingDataReader(filename='afl_betting.csv')
