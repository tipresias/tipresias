"""Module for FootywireDataImporter, which scrapes footywire.com.au for betting & match data"""

from typing import Optional, Tuple, Pattern
import warnings
import re
from datetime import date
from functools import partial
from urllib3.exceptions import SystemTimeWarning
import pandas as pd

from project.settings.common import DATA_DIR
from .base_data_importer import BaseDataImporter

FOOTY_WIRE_DOMAIN = "https://www.footywire.com"
FIXTURE_PATH = "/afl/footy/ft_match_list"
AFL_DATA_SERVICE = "http://afl_data:8001"
N_DATA_COLS = 7
N_USEFUL_DATA_COLS = 5
FIXTURE_COLS = [
    "Date",
    "Home v Away Teams",
    "Venue",
    "Crowd",
    "Result",
    "Round",
    "Season",
]
BETTING_MATCH_COLS = ["date", "venue", "round", "round_label", "season"]

INVALID_MATCH_REGEX = r"BYE|MATCH CANCELLED"
TEAM_SEPARATOR_REGEX = r"\sv\s"
RESULT_SEPARATOR = "-"
DIGITS: Pattern = re.compile(r"round\s+(\d+)$", flags=re.I)
QUALIFYING: Pattern = re.compile(r"qualifying", flags=re.I)
ELIMINATION: Pattern = re.compile(r"elimination", flags=re.I)
SEMI: Pattern = re.compile(r"semi", flags=re.I)
PRELIMINARY: Pattern = re.compile(r"preliminary", flags=re.I)
GRAND: Pattern = re.compile(r"grand", flags=re.I)
FINALS_WEEK: Pattern = re.compile(r"Finals\s+Week\s+(\d+)$", flags=re.I)
# One bloody week in 2010 uses 'One' instead of '1' on afl_betting
FINALS_WEEK_ONE: Pattern = re.compile(r"Finals\s+Week\s+One", flags=re.I)

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
        start_date: str = "1897-01-01",
        end_date: str = str(date.today()),
        fetch_data: bool = False,
    ) -> pd.DataFrame:
        """
        Get AFL betting data for given year range.

        Returns pandas.DataFrame with columns:
            date, venue, round, round_label, season, home_team, home_score, home_margin,
            home_win_odds, home_win_paid, home_line_odds, home_line_paid, away_team,
            away_score, away_margin, away_win_odds, away_win_paid, away_line_odds,
            away_line_paid
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
                .pipe(self.__clean_betting_data_frame)
                .pipe(self.__merge_home_away)
                .pipe(self.__sort_betting_columns)
            )

        start_year = int(start_date[:4])
        end_year = int(end_date[:4])

        return self.__read_data_csv(self.betting_filename, (start_year, end_year))

    def __read_data_csv(
        self, filename: str, year_range: Optional[Tuple[int, int]]
    ) -> pd.DataFrame:
        csv_data_frame = pd.read_csv(
            f"{self.csv_dir}/{filename}.csv", parse_dates=["date"]
        )

        if year_range is None:
            return csv_data_frame

        min_year, max_year = year_range

        return csv_data_frame[
            (csv_data_frame["season"] >= min_year)
            & (csv_data_frame["season"] < max_year)
        ]

    def __clean_betting_data_frame(self, data_frame: pd.DataFrame) -> pd.DataFrame:
        return data_frame.assign(
            date=self._parse_dates,
            round_label=lambda df: df["round"],
            round=self.__round_number,
        )

    def __merge_home_away(self, data_frame: pd.DataFrame) -> pd.DataFrame:
        return (
            self.__split_home_away(data_frame, "home")
            .merge(self.__split_home_away(data_frame, "away"), on=BETTING_MATCH_COLS)
            .sort_values("date", ascending=True)
            .drop_duplicates(
                subset=["home_team", "away_team", "season", "round_label"], keep="last"
            )
            .fillna(0)
        )

    @staticmethod
    def __sort_betting_columns(data_frame: pd.DataFrame) -> pd.DataFrame:
        sorted_cols = BETTING_MATCH_COLS + [
            col for col in data_frame.columns if col not in BETTING_MATCH_COLS
        ]

        return data_frame[sorted_cols]

    def __round_number(self, data_frame: pd.DataFrame) -> pd.Series:
        year_groups = data_frame.groupby("season")
        yearly_series_list = [
            self.__yearly_round_number(year_data_frame)
            for _, year_data_frame in year_groups
        ]

        return pd.concat(yearly_series_list)

    def __yearly_round_number(self, data_frame: pd.DataFrame) -> pd.Series:
        yearly_round_col = data_frame["round"]
        # Digit regex has to be at the end because betting round labels include
        # the year at the start
        round_numbers = yearly_round_col.str.extract(DIGITS, expand=False)
        max_regular_round = pd.to_numeric(round_numbers, errors="coerce").max()

        return yearly_round_col.map(
            partial(self.__parse_round_label, max_regular_round)
        )

    @staticmethod
    def __parse_round_label(max_regular_round: int, round_label: str) -> int:
        round_number = DIGITS.search(round_label)
        finals_week = FINALS_WEEK.search(round_label)

        if round_number is not None:
            return int(round_number.group(1))
        if finals_week is not None:
            # Betting data uses the format "YYYY Finals Week N" to label finals rounds
            # so we can just add N to max round to get the round number
            return int(finals_week.group(1)) + max_regular_round
        if (
            QUALIFYING.search(round_label) is not None
            or ELIMINATION.search(round_label) is not None
            or FINALS_WEEK_ONE.search(round_label) is not None
        ):
            # Basing finals round numbers on max regular season round number rather than
            # fixed values for consistency with other data sources
            return max_regular_round + 1
        if SEMI.search(round_label) is not None:
            return max_regular_round + 2
        if PRELIMINARY.search(round_label) is not None:
            return max_regular_round + 3
        if GRAND.search(round_label) is not None:
            return max_regular_round + 4

        raise ValueError(f"Round label {round_label} doesn't match any known patterns")

    @staticmethod
    def __split_home_away(data_frame: pd.DataFrame, team_type: str) -> pd.DataFrame:
        if team_type not in ["home", "away"]:
            raise ValueError(
                f"team_type must either be 'home' or 'away', but {team_type} was given."
            )

        # Raw betting data has two rows per match: the top team is home and the bottom
        # is away
        filter_remainder = 0 if team_type == "home" else 1
        row_filter = [n % 2 == filter_remainder for n in range(len(data_frame))]

        return data_frame[row_filter].rename(
            columns=lambda col: f"{team_type}_" + col
            if col not in BETTING_MATCH_COLS
            else col
        )
