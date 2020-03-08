# pylint: disable=missing-docstring
from django.test import TestCase
import pandas as pd

from server.helpers import pivot_team_matches_to_matches
from server.tests.fixtures.data_factories import fake_prediction_data


class TestHelpers(TestCase):
    def setUp(self):
        self.team_match_df = pd.DataFrame(fake_prediction_data())

    def test_pivot_team_matches_to_matches(self):
        match_df = pivot_team_matches_to_matches(self.team_match_df)

        self.assertIsInstance(match_df, pd.DataFrame)
        self.assertIn("home_team", match_df.columns)
        self.assertIn("away_team", match_df.columns)
        self.assertIn("home_predicted_margin", match_df.columns)
        self.assertIn("away_predicted_margin", match_df.columns)

        self.assertNotIn("team", match_df.columns)
        self.assertNotIn("oppo_team", match_df.columns)
