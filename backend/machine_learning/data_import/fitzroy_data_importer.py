import json
from typing import Dict, Any, List
from datetime import date
from urllib.parse import urljoin

import pandas as pd
import requests

from project.settings.common import MELBOURNE_TIMEZONE

TEAM_TRANSLATIONS = {
    "Brisbane Lions": "Brisbane",
    "Brisbane Bears": "Brisbane",
    "Greater Western Sydney": "GWS",
    "Footscray": "Western Bulldogs",
}

AFL_DATA_SERVICE = "http://afl_data:8001"


class FitzroyDataImporter:
    """Get data from the fitzRoy R package and return it as a pandas DataFrame."""

    def __init__(self, verbose=1):
        self.verbose = verbose

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

        data = self.__fetch_afl_data(
            "matches",
            params={
                "fetch_data": fetch_data,
                "start_date": start_date,
                "end_date": end_date,
            },
        )

        if self.verbose == 1:
            print("Match data received!")

        return (
            pd.DataFrame(data)
            .pipe(self.__parse_dates)
            .assign(
                home_team=self.__translate_team_column("home_team"),
                away_team=self.__translate_team_column("away_team"),
            )
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

        data = self.__fetch_afl_data(
            "players", params={"start_date": start_date, "end_date": end_date}
        )

        if self.verbose == 1:
            print("Player data received!")

        return (
            pd.DataFrame(data)
            .pipe(self.__parse_dates)
            .assign(
                home_team=self.__translate_team_column("home_team"),
                away_team=self.__translate_team_column("away_team"),
                playing_for=self.__translate_team_column("playing_for"),
            )
        )

    @staticmethod
    def __fetch_afl_data(
        path: str, params: Dict[str, Any] = {}
    ) -> List[Dict[str, Any]]:
        data = requests.get(urljoin(AFL_DATA_SERVICE, path), params=params).json()

        if isinstance(data, dict) and "error" in data.keys():
            raise RuntimeError(data["error"])

        if len(data) == 1:
            # For some reason, when returning match data with fetch_data=False,
            # plumber returns JSON as a big string inside a list, so we have to parse
            # the first element
            return json.loads(data[0])

        if any(data):
            return data

        return []

    @staticmethod
    def __parse_dates(data_frame: pd.DataFrame) -> pd.DataFrame:
        return data_frame.assign(
            date=lambda df: pd.to_datetime(data_frame["date"]).dt.tz_localize(
                MELBOURNE_TIMEZONE
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
