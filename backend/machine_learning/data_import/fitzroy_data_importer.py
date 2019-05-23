from datetime import date

import pandas as pd

from .base_data_importer import BaseDataImporter

TEAM_TRANSLATIONS = {
    "Brisbane Lions": "Brisbane",
    "Brisbane Bears": "Brisbane",
    "Greater Western Sydney": "GWS",
    "Footscray": "Western Bulldogs",
}


class FitzroyDataImporter(BaseDataImporter):
    """Get data from the fitzRoy R package and return it as a pandas DataFrame."""

    def __init__(self, verbose=1):
        super().__init__(verbose=verbose)

    def match_results(
        self,
        fetch_data: bool = False,
        start_date: str = "1897-01-01",
        end_date: str = str(date.today()),
    ) -> pd.DataFrame:
        """Get match results data.

        Args:
            fetch_data (boolean): Whether to fetch fresh data or use the match data
                that comes with the package.

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

        return pd.DataFrame(data).assign(
            date=self._parse_dates,
            home_team=self.__translate_team_column("home_team"),
            away_team=self.__translate_team_column("away_team"),
        )

    def get_afltables_stats(
        self, start_date: str = "1965-01-01", end_date: str = str(date.today())
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

        return (
            pd.DataFrame(data)
            .pipe(self._parse_dates)
            .assign(
                home_team=self.__translate_team_column("home_team"),
                away_team=self.__translate_team_column("away_team"),
                playing_for=self.__translate_team_column("playing_for"),
            )
        )

    def __translate_team_column(self, col_name):
        return lambda data_frame: data_frame[col_name].map(self.__translate_team_name)

    @staticmethod
    def __translate_team_name(team_name):
        return (
            TEAM_TRANSLATIONS[team_name]
            if team_name in TEAM_TRANSLATIONS
            else team_name
        )
