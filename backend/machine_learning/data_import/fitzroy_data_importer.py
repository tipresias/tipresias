from datetime import date

import pandas as pd

from .base_data_importer import BaseDataImporter

EARLIEST_FOOTYWIRE_SEASON = "1965"
EARLIEST_AFLTABLES_SEASON = "1897"


class FitzroyDataImporter(BaseDataImporter):
    """Get data from the fitzRoy R package and return it as a pandas DataFrame."""

    def __init__(self, verbose=1):
        super().__init__(verbose=verbose)

    def match_results(
        self,
        fetch_data: bool = False,
        start_date: str = f"{EARLIEST_AFLTABLES_SEASON}-01-01",
        end_date: str = str(date.today()),
    ) -> pd.DataFrame:
        """Get match results data.

        Args:
            fetch_data (boolean): Whether to fetch fresh data or use the match data
                that comes with the package.
            start_date (string: YYYY-MM-DD): Earliest date for match data returned.
            end_date (string: YYYY-MM-DD): Latest date for match data returned.

        Returns:
            pandas.DataFrame
        """

        if self.verbose == 1:
            print(f"Fetching match data from between {start_date} and {end_date}...")

        data = self._fetch_afl_data(
            "matches",
            params={
                "fetch_data": fetch_data,
                "start_date": start_date,
                "end_date": end_date,
            },
        )

        if self.verbose == 1:
            print("Match data received!")

        return pd.DataFrame(data).assign(date=self._parse_dates)

    def get_afltables_stats(
        self,
        start_date: str = f"{EARLIEST_FOOTYWIRE_SEASON}-01-01",
        end_date: str = str(date.today()),
    ) -> pd.DataFrame:
        """Get player data from AFL tables
        Args:
            start_date (string: YYYY-MM-DD): Earliest date for match data returned.
            end_date (string: YYYY-MM-DD): Latest date for match data returned.

        Returns:
            pandas.DataFrame
        """

        if self.verbose == 1:
            print(f"Fetching player data from between {start_date} and {end_date}...")

        data = self._fetch_afl_data(
            "players", params={"start_date": start_date, "end_date": end_date}
        )

        if self.verbose == 1:
            print("Player data received!")

        return pd.DataFrame(data).assign(date=self._parse_dates)

    def fetch_fixtures(
        self,
        start_date: str = f"{EARLIEST_FOOTYWIRE_SEASON}-01-01",
        end_date: str = str(date.today()),
    ) -> pd.DataFrame:
        """
        Get fixture data (unplayed matches) from Footywire (by way of fitzRoy)

        Args:
            start_date (string: YYYY-MM-DD): Earliest date for match data returned.
            end_date (string: YYYY-MM-DD): Latest date for match data returned.

        Returns:
            pandas.DataFrame
        """

        if self.verbose == 1:
            print(f"Fetching fixture data from between {start_date} and {end_date}...")

        data = self._fetch_afl_data(
            "fixtures", params={"start_date": start_date, "end_date": end_date}
        )

        if self.verbose == 1:
            print("Fixture data received!")

        return (
            pd.DataFrame(data)
            .assign(date=self._parse_dates)
            .drop("season_game", axis=1)
            .sort_values("date")
        )
