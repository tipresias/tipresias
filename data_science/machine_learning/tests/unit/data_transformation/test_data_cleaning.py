import os
from unittest import TestCase
from datetime import datetime
import pandas as pd
from faker import Faker

from machine_learning.data_transformation.data_cleaning import (
    clean_betting_data,
    clean_match_data,
    clean_player_data,
    clean_joined_data,
)
from machine_learning.settings import MELBOURNE_TIMEZONE

DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../fixtures"))
N_PLAYERS = 20
N_MATCHES = 5
FAKE = Faker()


class TestDataCleaning(TestCase):
    def test_clean_betting_data(self):
        betting_data = (
            pd.read_csv(os.path.join(DATA_DIR, "afl_betting.csv"), parse_dates=["date"])
            .assign(
                date=lambda df: pd.to_datetime(df["date"]).dt.tz_localize(
                    MELBOURNE_TIMEZONE
                )
            )
            .rename(columns={"round": "round_number", "round_label": "round"})
        )

        clean_data = clean_betting_data(betting_data)

        self.assertIsInstance(clean_data, pd.DataFrame)

        required_columns = ["home_team", "away_team", "year", "round_number"]

        for col in required_columns:
            self.assertTrue(col in clean_data.columns.values)

    def test_clean_match_data(self):
        match_data = pd.read_csv(os.path.join(DATA_DIR, "fitzroy_match_results.csv"))

        clean_data = clean_match_data(match_data)

        self.assertIsInstance(clean_data, pd.DataFrame)

        required_columns = ["home_team", "away_team", "year", "round_number"]

        for col in required_columns:
            self.assertTrue(col in clean_data.columns.values)

    def test_clean_player_data(self):
        match_data = pd.read_csv(os.path.join(DATA_DIR, "fitzroy_match_results.csv"))
        player_data = pd.read_csv(
            os.path.join(DATA_DIR, "fitzroy_get_afltables_stats.csv")
        )

        clean_data = clean_player_data(player_data, match_data)

        self.assertIsInstance(clean_data, pd.DataFrame)

        required_columns = ["home_team", "away_team", "year", "round_number"]

        for col in required_columns:
            self.assertTrue(col in clean_data.columns.values)

        with self.subTest("with roster data for upcoming matches"):
            roster_data = pd.DataFrame(
                {
                    "date": [datetime(2019, 3, 20, 7)] * N_PLAYERS,
                    "round_number": [1] * N_PLAYERS,
                    "year": [2019] * N_PLAYERS,
                    "match_id": list(range(N_PLAYERS)),
                    "playing_for": [FAKE.company() for _ in range(N_PLAYERS)],
                    "player_name": [
                        FAKE.first_name() + " " + FAKE.last_name()
                        for _ in range(N_PLAYERS)
                    ],
                    "home_team": [FAKE.company() for _ in range(N_PLAYERS)],
                    "away_team": [FAKE.company() for _ in range(N_PLAYERS)],
                }
            )

            clean_data = clean_player_data(
                player_data, match_data, roster_data=roster_data
            )

            self.assertIsInstance(clean_data, pd.DataFrame)

            this_year_data = clean_data.query("year == 2019")

            self.assertTrue(this_year_data.any().any())

    def test_clean_joined_data(self):
        match_data = pd.read_csv(os.path.join(DATA_DIR, "fitzroy_match_results.csv"))
        player_data = pd.read_csv(
            os.path.join(DATA_DIR, "fitzroy_get_afltables_stats.csv")
        )
        betting_data = pd.read_csv(os.path.join(DATA_DIR, "afl_betting.csv"))

        clean_data = clean_joined_data([player_data, match_data, betting_data])

        self.assertIsInstance(clean_data, pd.DataFrame)

        are_duplicate_columns = pd.concat(
            [
                pd.Series(match_data.columns),
                pd.Series(player_data.columns),
                pd.Series(betting_data.columns),
            ]
        ).duplicated()
        self.assertTrue(are_duplicate_columns.any())
        are_duplicate_clean_columns = clean_data.columns.duplicated()
        self.assertFalse(are_duplicate_clean_columns.any())
