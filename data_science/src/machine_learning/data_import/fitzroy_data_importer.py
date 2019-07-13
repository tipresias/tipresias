from datetime import date, datetime, timedelta
from typing import List, Dict, Any
import itertools
import math
from functools import partial

import pandas as pd

from .base_data_importer import BaseDataImporter

EARLIEST_FOOTYWIRE_SEASON = "1965"
EARLIEST_AFLTABLES_SEASON = "1897"
# This is the max number of season's worth of player data (give or take) that GCR
# can handle without blowing up
MAX_YEAR_COUNT_FOR_PLAYER_DATA = 3


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

        if not any(data):
            if self.verbose == 1:
                print(
                    f"No match results data found for {start_date} to {end_date}, "
                    "returning empty data frame"
                )

            return pd.DataFrame()

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
            print(
                f"Fetching player data from between {start_date} and {end_date} "
                "in yearly baches..."
            )

        data_batch_date_ranges = self._player_batch_date_ranges(start_date, end_date)

        # TODO: Temporary(?) solution to the issue of GCR not being able to handle such a
        # large data set. The documentation isn't too clear, but I might be able to
        # dump the full set in a storage bucket and retrieve it from there, but this
        # is good enough for now.
        data = itertools.chain.from_iterable(
            [
                self._fetch_player_stats_batch(*date_pair)
                for date_pair in data_batch_date_ranges
            ]
        )

        if self.verbose == 1:
            print("All player data received!")

        return pd.DataFrame(list(data)).assign(date=self._parse_dates)

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
            print(f"Fetching fixture data from between {start_date} and {end_date}")

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

    def _player_batch_date_ranges(self, start_date: str, end_date: str):
        start_date_dt = datetime.strptime(start_date, "%Y-%m-%d")
        end_date_dt = datetime.strptime(end_date, "%Y-%m-%d")
        time_spread = timedelta(days=(MAX_YEAR_COUNT_FOR_PLAYER_DATA * 365))
        year_spread = (end_date_dt - start_date_dt) / time_spread

        date_range = partial(self._date_range, start_date_dt, end_date_dt, time_spread)

        return [date_range(period) for period in range(math.ceil(year_spread))]

    @staticmethod
    def _date_range(
        start_date: datetime, end_date: datetime, time_spread: timedelta, period: int
    ):
        range_start = start_date + (time_spread * period)
        range_end = min(range_start + time_spread - timedelta(days=1), end_date)

        return (str(range_start.date()), str(range_end.date()))

    def _fetch_player_stats_batch(
        self, start_date: str, end_date: str
    ) -> List[Dict[str, Any]]:  # Just being lazy on the definition
        if self.verbose == 1:
            print(
                f"\tFetching player data from between {start_date} and "
                f"{end_date}..."
            )

        data = self._fetch_afl_data(
            "players", params={"start_date": start_date, "end_date": end_date}
        )

        if self.verbose == 1:
            print(f"\tPlayer data for {start_date} to {end_date} received!\n")

        return data
