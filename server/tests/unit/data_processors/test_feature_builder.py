import os
import sys
from unittest import TestCase
from faker import Faker
import pandas as pd
import numpy as np

PROJECT_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '../../../')
)

if PROJECT_PATH not in sys.path:
    sys.path.append(PROJECT_PATH)

from server.data_processors import FeatureBuilder
from server.data_processors.feature_builder import REQUIRED_COLS

FAKE = Faker()


class TestFeatureBuilder(TestCase):
    def setUp(self):
        feature_funcs = [
            lambda df: df.assign(new_col=[FAKE.name() for _ in range(10)]),
            lambda df: df.assign(newer_col=df['new_col'] + ' but even newer')
        ]
        self.builder = FeatureBuilder(feature_funcs=feature_funcs)

    def test_transform(self):
        teams = [FAKE.company() for _ in range(10)]
        oppo_teams = list(reversed(teams))

        valid_data_frame = pd.DataFrame({
            'team': teams,
            'oppo_team': oppo_teams,
            'year': [2015 for _ in range(10)],
            'round_number': [3 for _ in range(10)],
            'score': [np.random.randint(50, 150) for _ in range(10)],
            'oppo_score': [np.random.randint(50, 150) for _ in range(10)]
        }).set_index(['year', 'round_number', 'team'], drop=False)

        with self.subTest(data_frame=valid_data_frame):
            data_frame = valid_data_frame

            transformed_df = self.builder.transform(data_frame)

            # FeatureBuilder adds 1 column per function
            self.assertEqual(len(data_frame.columns) + 2,
                             len(transformed_df.columns))

            # Should add the two new columns and their 'oppo_' equivalents
            self.assertIn('new_col', transformed_df.columns)
            self.assertIn('newer_col', transformed_df.columns)

        for required_col in REQUIRED_COLS:
            with self.subTest(data_frame=valid_data_frame.drop(required_col, axis=1)):
                data_frame = valid_data_frame.drop(required_col, axis=1)

                with self.assertRaises(ValueError):
                    self.builder.transform(data_frame)
