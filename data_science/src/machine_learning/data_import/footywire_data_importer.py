"""Module for FootywireDataImporter, which scrapes footywire.com.au for betting & match data"""

from typing import Optional, Tuple
import os
import warnings
from datetime import date
from urllib3.exceptions import SystemTimeWarning
import pandas as pd

from machine_learning.settings import DATA_DIR
from .base_data_importer import BaseDataImporter

AFL_DATA_SERVICE = "http://afl_data:8001"
BETTING_MATCH_COLS = ["date", "venue", "round", "round_number", "season"]
FIRST_YEAR_OF_BETTING_DATA = 2010

# I get this warning when I run tests, but not in other contexts
warnings.simplefilter("ignore", SystemTimeWarning)


class FootywireDataImporter(BaseDataImporter):
    """Get data from footywire.com.au by scraping page or reading saved CSV"""

    def __init__(
        self,
        csv_dir: str = DATA_DIR,
        fixture_filename: str = "ft_match_list",
        betting_filename: str = "afl_betting",
        verbose=1,
    ) -> None:
        super().__init__(verbose=verbose)
        self.csv_dir = csv_dir
        self.fixture_filename = fixture_filename
        self.betting_filename = betting_filename

    def get_betting_odds(
        self,
        start_date: str = f"{FIRST_YEAR_OF_BETTING_DATA}-01-01",
        end_date: str = str(date.today()),
        fetch_data: bool = False,
    ) -> pd.DataFrame:
        """
        Get AFL betting data for given year range.

        Args:
            start_date (string: YYYY-MM-DD): Earliest date for match data returned.
            end_date (string: YYYY-MM-DD): Latest date for match data returned.
            fetch_data (boolean): Whether to fetch fresh data or use the match data
                that comes with the package.

        Returns
            pandas.DataFrame
        """

        if fetch_data:
            if self.verbose == 1:
                print(
                    "Fetching betting odds data from between "
                    f"{start_date} and {end_date}..."
                )

            data = self._fetch_afl_data(
                "betting_odds", params={"start_date": start_date, "end_date": end_date}
            )

            if self.verbose == 1:
                print("Betting odds data received!")

            return (
                pd.DataFrame(data)
                .assign(date=self._parse_dates)
                .pipe(self.__sort_betting_columns)
            )

        start_year = int(start_date[:4])
        end_year = int(end_date[:4])

        return self.__read_data_csv(self.betting_filename, (start_year, end_year))

    def __read_data_csv(
        self, filename: str, year_range: Optional[Tuple[int, int]]
    ) -> pd.DataFrame:
        csv_data_frame = (
            pd.read_csv(
                os.path.join(self.csv_dir, f"{filename}.csv"), parse_dates=["date"]
            )
            .assign(date=self._parse_dates)
            .rename(columns={"round": "round_number", "round_label": "round"})
        )

        if year_range is None:
            return csv_data_frame

        min_year, max_year = year_range

        return csv_data_frame[
            (csv_data_frame["season"] >= min_year)
            & (csv_data_frame["season"] < max_year)
        ]

    @staticmethod
    def __sort_betting_columns(data_frame: pd.DataFrame) -> pd.DataFrame:
        sorted_cols = BETTING_MATCH_COLS + [
            col for col in data_frame.columns if col not in BETTING_MATCH_COLS
        ]

        return data_frame[sorted_cols]
