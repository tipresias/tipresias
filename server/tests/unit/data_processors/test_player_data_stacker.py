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

from server.data_processors import PlayerDataStacker
from server.data_processors.player_data_stacker import REQUIRED_COLS

FAKE = Faker()


class TestPlayerDataStacker(TestCase):
    def setUp(self):
        self.transformer = PlayerDataStacker()

        home_teams = [FAKE.company() for _ in range(10)]
        away_teams = [FAKE.company() for _ in range(10)]
        self.data_frame = pd.DataFrame({
            'home_team': home_teams,
            'away_team': away_teams,
            'playing_for': home_teams[:5] + away_teams[5:],
            'year': [FAKE.year() for _ in range(10)],
            'match_id': np.random.randint(100, 200, 10),
            'home_score': np.random.randint(50, 150, 10),
            'away_score': np.random.randint(50, 150, 10)
        })

    def test_transform(self):
        valid_data_frame = self.data_frame

        with self.subTest(data_frame=valid_data_frame):
            transformed_df = self.transformer.transform(valid_data_frame)

            self.assertIsInstance(transformed_df, pd.DataFrame)
            # Splitting home & away for player data doesn't change row count
            self.assertEqual(len(valid_data_frame), len(transformed_df))
            # 'home_'/'away_' columns become regular columns or 'oppo_' columns,
            # non-team-specific columns are unchanged.
            # We add 'at_home', but drop 'match_id' & 'playing_for'
            self.assertEqual(len(valid_data_frame.columns) - 1,
                             len(transformed_df.columns))
            self.assertIn('at_home', transformed_df.columns)
            # Half the teams should be marked as 'at_home'
            self.assertEqual(transformed_df['at_home'].sum(),
                             len(transformed_df) / 2)

        for required_col in REQUIRED_COLS:
            invalid_data_frame = self.data_frame.drop(required_col, axis=1)

            with self.subTest(data_frame=invalid_data_frame):
                with self.assertRaises(ValueError):
                    self.transformer.transform(invalid_data_frame)
