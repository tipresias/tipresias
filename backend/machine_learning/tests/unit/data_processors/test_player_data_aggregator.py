from unittest import TestCase
from faker import Faker
import pandas as pd
import numpy as np

from machine_learning.data_processors import PlayerDataAggregator
from machine_learning.data_processors.player_data_aggregator import REQUIRED_COLS, STATS_COLS

FAKE = Faker()
N_ROWS = 10


class TestPlayerDataAggregator(TestCase):
    def setUp(self):
        self.index_cols = ["team", "year", "round_number"]
        self.transformer = PlayerDataAggregator(
            index_cols=self.index_cols, aggregations=["sum", "std"]
        )

        teams = [FAKE.company(), FAKE.company()]
        self.data_frame = pd.DataFrame(
            {
                **{
                    "team": sorted(teams * int(N_ROWS / 2)),
                    "oppo_team": list(reversed(sorted(teams * int(N_ROWS / 2)))),
                    "year": [2014] * N_ROWS,
                    "round_number": [12] * N_ROWS,
                    "score": np.random.randint(50, 150, N_ROWS),
                    "oppo_score": np.random.randint(50, 150, N_ROWS),
                    "at_home": ([1] * 5) + ([0] * 5),
                    "player_id": [n for n in range(N_ROWS)],
                    "player_name": [FAKE.name() for _ in range(N_ROWS)],
                },
                **{
                    stats_col: np.random.randint(0, 20, N_ROWS)
                    for stats_col in STATS_COLS
                },
            }
        )

    def test_transform(self):
        valid_data_frame = self.data_frame

        with self.subTest(data_frame=valid_data_frame):
            transformed_df = self.transformer.transform(valid_data_frame)

            self.assertIsInstance(transformed_df, pd.DataFrame)

            # We drop player_id & player_name, but add new stats cols for each aggregation
            expected_col_count = len(valid_data_frame.columns) - 2 + len(STATS_COLS)
            self.assertEqual(expected_col_count, len(transformed_df.columns))

            # Match data should remain unchanged (requires a little extra manipulation,
            # because I can't be bothred to make the score data realistic)
            for idx, value in (
                enumerate(valid_data_frame.groupby("team")["score"].mean().astype(int))
            ):
                self.assertEqual(value, transformed_df["score"].iloc[idx])

            for idx, value in (
                enumerate(valid_data_frame.groupby("team")["oppo_score"].mean().astype(int))
            ):
                self.assertEqual(value, transformed_df["oppo_score"].iloc[idx])

            # Player data should be aggregated, but same sum
            self.assertEqual(
                valid_data_frame["rolling_prev_match_kicks"].sum(),
                transformed_df["rolling_prev_match_kicks_sum"].sum(),
            )

        for required_col in REQUIRED_COLS + self.index_cols:
            invalid_data_frame = self.data_frame.drop(required_col, axis=1)

            with self.subTest(data_frame=invalid_data_frame):
                with self.assertRaises(ValueError):
                    self.transformer.transform(invalid_data_frame)
