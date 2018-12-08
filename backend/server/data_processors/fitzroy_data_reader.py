from typing import Optional
import pandas as pd
from rpy2.robjects import pandas2ri, vectors, r


TEAM_TRANSLATIONS = {
    "Brisbane Lions": "Brisbane",
    "Brisbane Bears": "Brisbane",
    "Greater Western Sydney": "GWS",
    "Footscray": "Western Bulldogs",
}


class FitzroyDataReader:
    """Get data from the fitzRoy R package and return it as a pandas DataFrame."""

    def match_results(self, fetch_data: bool = False) -> pd.DataFrame:
        """Get match results data.

        Args:
            fetch_data (boolean): Whether to fetch fresh data or use the match data
                that comes with the package.

        Returns:
            pandas.DataFrame
        """

        method_string = "get_match_results()" if fetch_data else "match_results"

        return self.__data(method_string)

    def get_afltables_stats(
        self,
        start_date: Optional[str] = "1965-01-01",
        end_date: Optional[str] = "2016-12-31",
    ) -> pd.DataFrame:
        """Get player data from AFL tables
        Args:
            start_date (string: YYYY-MM-DD): Earliest date for match data returned.
            end_date (string: YYYY-MM-DD): Latest date for match data returned.

        Returns:
            pandas.DataFrame
        """

        return self.__data(
            f'get_afltables_stats(start_date = "{start_date}", '
            f'end_date = "{end_date}")'
        ).assign(playing_for=self.__translate_team_column("playing_for"))

    def __data(self, method_string: str):
        return self.__r_to_pandas(r(f"fitzRoy::{method_string}")).assign(
            home_team=self.__translate_team_column("home_team"),
            away_team=self.__translate_team_column("away_team"),
        )

    def __translate_team_column(self, col_name):
        return lambda data_frame: data_frame[col_name].map(self.__translate_teams)

    @staticmethod
    def __r_to_pandas(r_data_frame: vectors.DataFrame) -> pd.DataFrame:
        return pandas2ri.ri2py(r_data_frame).rename(
            columns=lambda x: x.lower().replace(".", "_")
        )

    @staticmethod
    def __translate_teams(team_name):
        return (
            TEAM_TRANSLATIONS[team_name]
            if team_name in TEAM_TRANSLATIONS
            else team_name
        )
