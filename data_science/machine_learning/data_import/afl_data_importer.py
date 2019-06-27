"""Module for fetching scraped data from afl.com.au via the afl_data service"""

import pandas as pd

from .base_data_importer import BaseDataImporter


class AflDataImporter(BaseDataImporter):
    """Get data from the official AFL site and return it as a pandas DataFrame."""

    def __init__(self, verbose=1):
        super().__init__(verbose=verbose)

    def fetch_rosters(self, round_number: int) -> pd.DataFrame:
        """
        Fetches roster data for the upcoming round from afl.com.au

        Args:
            round_number (int): Fetch rosters for this round, current or most-recently
                played season only. Data for future rounds are not available.

        Returns:
            pandas.DataFrame
        """

        if self.verbose == 1:
            print(f"Fetching roster data for round {round_number}...")

        data = self._fetch_afl_data("rosters", params={"round_number": round_number})

        if not any(data):
            return self.__return_empty_data_frame(round_number)

        if self.verbose == 1:
            print("Roster data received!")

        return pd.DataFrame(data).assign(date=self._parse_dates)

    def __return_empty_data_frame(self, round_number: int) -> pd.DataFrame:
        if self.verbose == 1:
            print(
                f"No roster data available for round {round_number} yet, returning "
                "an empty data frame."
            )

        return pd.DataFrame(
            columns=[
                "date",
                "round_number",
                "season",
                "match_id",
                "playing_for",
                "player_name",
                "home_team",
                "away_team",
            ]
        )
