import os
from unittest import TestCase
import pandas as pd
import numpy as np
from faker import Faker

from machine_learning.data_transformation.data_cleaning import (
    clean_betting_data,
    clean_match_data,
    clean_player_data,
)

DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../fixtures"))
N_PLAYERS = 10
FAKE = Faker()


class TestDataCleaning(TestCase):
    def test_clean_betting_data(self):
        betting_data = pd.read_csv(os.path.join(DATA_DIR, "afl_betting.csv"))
        match_data = pd.read_csv(os.path.join(DATA_DIR, "ft_match_list.csv"))

        clean_data = clean_betting_data(betting_data, match_data)

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
