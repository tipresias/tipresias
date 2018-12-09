from unittest import TestCase
from faker import Faker
import pandas as pd
import numpy as np

from server.data_processors import PlayerDataAggregator
from server.data_processors.player_data_aggregator import REQUIRED_COLS, STATS_COLS

FAKE = Faker()


class TestPlayerDataAggregator(TestCase):
    def setUp(self):
        self.index_cols = ["team", "year", "round_number"]
        self.transformer = PlayerDataAggregator(index_cols=self.index_cols)
        self.data_frame = pd.DataFrame(
            {
                **{
                    "team": [FAKE.company() for _ in range(10)],
                    "oppo_team": [FAKE.company() for _ in range(10)],
                    "year": [FAKE.year() for _ in range(10)],
                    "round_number": [12 for _ in range(10)],
                    "score": np.random.randint(50, 150, 10),
                    "oppo_score": np.random.randint(50, 150, 10),
                    "at_home": ([1] * 5) + ([0] * 5),
                    "player_id": [n % 3 for n in range(10)],
                    "player_name": [FAKE.name() for _ in range(10)],
                },
                **{stats_col: np.random.randint(0, 20, 10) for stats_col in STATS_COLS},
            }
        )

    def test_transform(self):
        valid_data_frame = self.data_frame

        with self.subTest(data_frame=valid_data_frame):
            transformed_df = self.transformer.transform(valid_data_frame)

            self.assertIsInstance(transformed_df, pd.DataFrame)

            # We drop player_id & player_name
            self.assertEqual(
                len(valid_data_frame.columns) - 2, len(transformed_df.columns)
            )
            # Match data should remain unchanged
            self.assertEqual(
                valid_data_frame["score"].mean(), transformed_df["score"].mean()
            )
            self.assertEqual(
                valid_data_frame["oppo_score"].mean(),
                transformed_df["oppo_score"].mean(),
            )
            # Player data should be aggregated, but same sum
            self.assertEqual(
                valid_data_frame["rolling_prev_match_kicks"].sum(),
                transformed_df["rolling_prev_match_kicks"].sum(),
            )
            self.assertEqual(
                valid_data_frame["rolling_prev_match_marks"].sum(),
                transformed_df["rolling_prev_match_marks"].sum(),
            )

        for required_col in REQUIRED_COLS + self.index_cols:
            invalid_data_frame = self.data_frame.drop(required_col, axis=1)

            with self.subTest(data_frame=invalid_data_frame):
                with self.assertRaises(ValueError):
                    self.transformer.transform(invalid_data_frame)
