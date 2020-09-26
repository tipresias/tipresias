# pylint: disable=missing-docstring

from unittest import TestCase

import pandas as pd
import numpy as np

from tests.fixtures.data_factories import fake_prediction_data, fake_match_data
from tipping.helpers import pivot_team_matches_to_matches, convert_to_dict


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

    def test_convert_to_dict(self):
        match_df = fake_match_data()
        match_df.loc[:, "crowd"] = np.nan
        match_records = convert_to_dict(match_df)

        # It converts the df to a list of dicts
        self.assertIsInstance(match_records, list)
        self.assertIsInstance(match_records[0], dict)
        self.assertEqual(set(match_df.columns), set(match_records[0].keys()))

        # It converts pandas/numpy dtypes to Python equivalents
        for match in match_records:
            self.assertEqual(match["crowd"], None)
            self.assertIsInstance(match["date"], str)
