from unittest import TestCase
from faker import Faker
import pandas as pd
import numpy as np

from machine_learning.data_processors import PlayerDataAggregator
from machine_learning.data_processors.player_data_aggregator import (
    REQUIRED_COLS,
    STATS_COLS,
)
from tests.fixtures.data_factories import fake_cleaned_player_data

FAKE = Faker()
N_MATCHES_PER_YEAR = 10
YEAR_RANGE = (2014, 2015)
N_PLAYERS_PER_TEAM = 10
# Need to multiply by two, because we add team & oppo_team row per match
N_ROWS = N_MATCHES_PER_YEAR * len(range(*YEAR_RANGE)) * N_PLAYERS_PER_TEAM * 2


class TestPlayerDataAggregator(TestCase):
    def setUp(self):
        self.index_cols = ["team", "year", "round_number"]
        self.transformer = PlayerDataAggregator(
            index_cols=self.index_cols, aggregations=["sum", "std"]
        )

        stats_col_assignments = {
            stats_col: np.random.randint(0, 20, N_ROWS) for stats_col in STATS_COLS
        }
        self.data_frame = (
            fake_cleaned_player_data(
                N_MATCHES_PER_YEAR, YEAR_RANGE, N_PLAYERS_PER_TEAM
            ).assign(**stats_col_assignments)
            # Drop 'playing_for', because it gets dropped by PlayerDataStacker,
            # which comes before PlayerDataAggregator in the pipeline
            .drop("playing_for", axis=1)
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
            for idx, value in enumerate(
                valid_data_frame.groupby(["team", "year", "round_number"])["score"]
                .mean()
                .astype(int)
            ):
                self.assertEqual(value, transformed_df["score"].iloc[idx])

            for idx, value in enumerate(
                valid_data_frame.groupby(["team", "year", "round_number"])["oppo_score"]
                .mean()
                .astype(int)
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
