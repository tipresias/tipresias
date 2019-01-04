"""Module for FootyWireDataReader, which scrapes footywire.com.au for betting & match data"""

from typing import Optional, Tuple, List, Sequence, Pattern
import re
from datetime import datetime
from urllib.parse import urljoin
from functools import reduce, partial
import dateutil
import requests
from bs4 import BeautifulSoup, element
import numpy as np
import pandas as pd

from project.settings.common import DATA_DIR

FOOTY_WIRE_DOMAIN = "https://www.footywire.com/afl/footy"
FIXTURE_PATH = "/ft_match_list"
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
INVALID_MATCH_REGEX = r"BYE|MATCH CANCELLED"
TEAM_SEPARATOR_REGEX = r"\sv\s"
RESULT_SEPARATOR = "-"
DIGITS: Pattern = re.compile(r"round\s+(\d+)$", flags=re.I)
QUALIFYING: Pattern = re.compile(r"qualifying", flags=re.I)
ELIMINATION: Pattern = re.compile(r"elimination", flags=re.I)
SEMI: Pattern = re.compile(r"semi", flags=re.I)
PRELIMINARY: Pattern = re.compile(r"preliminary", flags=re.I)
GRAND: Pattern = re.compile(r"grand", flags=re.I)


class FootyWireDataReader:
    """Get data from footywire.com.au by scraping page or reading saved CSV"""

    def __init__(
        self, csv_dir: str = DATA_DIR, fixture_filename: str = "ft_match_list"
    ) -> None:
        self.csv_dir = csv_dir
        self.fixture_filename = fixture_filename

    def get_fixture(
        self, year_range: Optional[Tuple[int, int]] = None, fresh_data: bool = False
    ) -> Optional[pd.DataFrame]:
        """Get AFL fixtures for given year range"""

        if fresh_data:
            return self.__clean_fixture_data_frame(
                self.__fetch_fixture_data(year_range)
            )

        return self.__read_fixture_csv(year_range)

    def __read_fixture_csv(self, year_range: Optional[Tuple[int, int]]) -> pd.DataFrame:
        csv_data_frame = pd.read_csv(
            f"{self.csv_dir}/{self.fixture_filename}.csv", parse_dates=["date"]
        )

        if year_range is None:
            return csv_data_frame

        min_year, max_year = year_range

        return csv_data_frame[
            (csv_data_frame["season"] >= min_year)
            & (csv_data_frame["season"] < max_year)
        ]

    def __fetch_fixture_data(
        self, year_range: Optional[Tuple[int, int]]
    ) -> pd.DataFrame:
        requested_year_range = year_range or (0, datetime.now().year + 1)
        yearly_fixture_data = []

        # Counting backwards to make sure we get all available years when year_range
        # is None
        for year in reversed(range(*requested_year_range)):
            year_data = self.__fetch_fixture_year(year)

            if year_data is None:
                break

            yearly_fixture_data.append(year_data)

        if len(yearly_fixture_data) == 0:
            raise ValueError(
                f"No data was found for the year range: {requested_year_range}"
            )

        fixture_data = self.__reduce_array_dimension(yearly_fixture_data)

        return pd.DataFrame(fixture_data, columns=FIXTURE_COLS)

    def __fetch_fixture_year(self, year: int) -> Optional[List[np.ndarray]]:
        res = requests.get(
            urljoin(FOOTY_WIRE_DOMAIN, FIXTURE_PATH), params={"year": year}
        )
        # Have to use html5lib, because default HTML parser wasn't working for this site
        soup = BeautifulSoup(res.text, "html5lib")
        # CSS selector for elements with round labels and all table data
        data_html = soup.select(".tbtitle,.data")

        if not any(data_html):
            return None

        round_groups = self.__group_by_round(data_html)
        get_fixture_data = partial(self.__get_fixture_data, year)
        grouped_data = [get_fixture_data(round_group) for round_group in round_groups]

        return self.__reduce_array_dimension(grouped_data)

    def __clean_fixture_data_frame(self, data_frame: pd.DataFrame) -> pd.DataFrame:
        valid_data_frame = (
            data_frame[~(data_frame["Venue"].str.contains(INVALID_MATCH_REGEX))]
            # Gotta drop duplicates, because St Kilda & Carlton tied a Grand Final
            # in 2010 and had to replay it, so let's just pretend that never happened
            .drop_duplicates(
                subset=["Home v Away Teams", "Season", "Round"], keep="last"
            )
            # Need to combine teams, year, & round to guarantee unique index.
            # NOTE: I tried using datetime, but older matches only have date, which
            # isn't unique with season + venue
            .assign(
                index=lambda df: df["Home v Away Teams"] + df["Season"] + df["Round"]
            ).set_index("index")
        )

        team_data_frame = (
            valid_data_frame["Home v Away Teams"]
            .str.split(TEAM_SEPARATOR_REGEX, expand=True)
            .rename(columns={0: "home_team", 1: "away_team"})
        )

        score_data_frame = (
            valid_data_frame["Result"]
            .str.split(RESULT_SEPARATOR, expand=True)
            .rename(columns={0: "home_score", 1: "away_score"})
            # For unplayed matches we convert scores to numeric, filling the resulting
            # NaNs with 0
            .assign(
                home_score=lambda df: pd.to_numeric(df["home_score"], errors="coerce"),
                away_score=lambda df: pd.to_numeric(df["home_score"], errors="coerce"),
            )
            .fillna(0)
        )

        cleaned_data_frame = (
            valid_data_frame.drop(["Home v Away Teams", "Result"], axis=1)
            .rename(columns=lambda col: col.lower().replace(r"\s", "_"))
            .assign(
                date=self.__parse_dates,
                round_label=lambda df: df["round"],
                crowd=lambda df: pd.to_numeric(df["crowd"], errors="coerce").fillna(0),
            )
            # Labelling round strings as 'round_label' and round numbers as 'round'
            # for consistency with fitzRoy column labels.
            # 'round' assignment depends on 'season' column so must come after.
            .assign(round=self.__round_number)
            .astype({"season": int})
        )

        return (
            pd.concat([cleaned_data_frame, team_data_frame, score_data_frame], axis=1)
            .reset_index(drop=True)
            .sort_values("date")
        )

    def __round_number(self, data_frame: pd.DataFrame) -> pd.Series:
        year_groups = data_frame.groupby("season")
        yearly_series_list = [
            self.__yearly_round_number(year_data_frame)
            for _, year_data_frame in year_groups
        ]

        return pd.concat(yearly_series_list)

    def __yearly_round_number(self, data_frame: pd.DataFrame) -> pd.Series:
        yearly_round_col = data_frame["round"]
        round_numbers = yearly_round_col.str.extract(r"(\d+)", expand=False)
        max_regular_round = pd.to_numeric(round_numbers, errors="coerce").max()

        return yearly_round_col.map(
            partial(self.__parse_round_label, max_regular_round)
        )

    @staticmethod
    def __get_fixture_data(year: int, round_group: List[element.Tag]) -> np.ndarray:
        round_label = next(round_group[0].stripped_strings)
        round_strings = [
            # Some data elements break up the interior text with interior html elements,
            # meaning the text is sometimes broken up, resulting in multiple stripped
            # strings per element
            " ".join(list(element.stripped_strings))
            for element in round_group[1:]
        ]
        round_table = np.reshape(round_strings, (-1, N_DATA_COLS))
        row_count = len(round_table)
        round_label_column = np.repeat(round_label, row_count).reshape(-1, 1)
        season_column = np.repeat(year, row_count).reshape(-1, 1)

        return np.concatenate(
            [round_table[:, :N_USEFUL_DATA_COLS], round_label_column, season_column],
            axis=1,
        )

    @staticmethod
    def __group_by_round(data_html: List[element.Tag]) -> List[List[element.Tag]]:
        are_round_labels = ["tbtitle" in element.get("class") for element in data_html]
        round_row_indices = np.argwhere(are_round_labels).flatten()
        round_groups = []

        for idx, lower_bound in enumerate(round_row_indices):
            if idx + 1 < len(round_row_indices):
                round_groups.append(data_html[lower_bound : round_row_indices[idx + 1]])
            else:
                round_groups.append(data_html[lower_bound:])

        return round_groups

    @staticmethod
    def __reduce_array_dimension(arrays: Sequence[np.ndarray]) -> np.ndarray:
        return reduce(
            lambda acc_arr, curr_arr: np.append(acc_arr, curr_arr, axis=0), arrays
        )

    @staticmethod
    def __parse_dates(data_frame: pd.DataFrame) -> pd.Series:
        # Need to add season to yearless date; otherwise, the date parser thinks they're
        # all in the current year.
        # MyPy doesn't recognize that dateutil has a 'parser' attribute
        return (data_frame["date"] + " " + data_frame["season"]).map(
            dateutil.parser.parse  # type: ignore
        )

    @staticmethod
    def __parse_round_label(max_regular_round: int, round_label: str) -> int:
        digits = DIGITS.search(round_label)

        # Basing finals round numbers on max regular season round number rather than
        # fixed values for consistency with other data sources
        if digits is not None:
            return int(digits.group(1))
        if (
            QUALIFYING.search(round_label) is not None
            or ELIMINATION.search(round_label) is not None
        ):
            return max_regular_round + 1
        if SEMI.search(round_label) is not None:
            return max_regular_round + 2
        if PRELIMINARY.search(round_label) is not None:
            return max_regular_round + 3
        if GRAND.search(round_label) is not None:
            return max_regular_round + 4

        raise ValueError(f"Round label {round_label} doesn't match any known patterns")
