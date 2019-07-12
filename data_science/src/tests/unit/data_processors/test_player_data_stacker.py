from unittest import TestCase
from faker import Faker
import pandas as pd

from machine_learning.data_processors import PlayerDataStacker
from machine_learning.data_processors.player_data_stacker import REQUIRED_COLS
from tests.fixtures.data_factories import fake_cleaned_player_data

FAKE = Faker()
N_MATCHES_PER_YEAR = 10
YEAR_RANGE = (2015, 2017)
N_PLAYERS_PER_TEAM = 10
# Need to multiply by two, because we add team & oppo_team row per match
N_ROWS = N_MATCHES_PER_YEAR * len(range(*YEAR_RANGE)) * 2 * N_PLAYERS_PER_TEAM


class TestPlayerDataStacker(TestCase):
    def setUp(self):
        self.transformer = PlayerDataStacker()

        self.data_frame = (
            fake_cleaned_player_data(N_MATCHES_PER_YEAR, YEAR_RANGE, N_PLAYERS_PER_TEAM)
            .assign(match_id=lambda df: df["date"])
            .rename(
                columns={
                    "team": "home_team",
                    "oppo_team": "away_team",
                    "score": "home_score",
                    "oppo_score": "away_score",
                }
            )
        )

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
            self.assertEqual(
                len(valid_data_frame.columns) - 1, len(transformed_df.columns)
            )
            self.assertIn("at_home", transformed_df.columns)
            # Half the teams should be marked as 'at_home'
            self.assertEqual(transformed_df["at_home"].sum(), len(transformed_df) / 2)

        for required_col in REQUIRED_COLS:
            invalid_data_frame = self.data_frame.drop(required_col, axis=1)

            with self.subTest(data_frame=invalid_data_frame):
                with self.assertRaises(ValueError):
                    self.transformer.transform(invalid_data_frame)
