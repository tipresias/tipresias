"""Module for FootywireDataImporter, which scrapes footywire.com.au for betting & match data"""

from typing import Optional, Tuple, List, Pattern
import warnings
import itertools
import re
from datetime import date
from urllib.parse import urljoin
from functools import partial
from urllib3.exceptions import SystemTimeWarning
import requests
from bs4 import BeautifulSoup, element
import numpy as np
import pandas as pd

from project.settings.common import DATA_DIR

FOOTY_WIRE_DOMAIN = "https://www.footywire.com"
FIXTURE_PATH = "/afl/footy/ft_match_list"
BETTING_PATH = "/afl/footy/afl_betting"
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
BETTING_COLS = [
    "Date",
    "Venue",
    "Team",
    "Score",
    "Margin",
    "Win Odds",
    "Win Paid",
    "Line Odds",
    "colon",
    "redundant_line_paid",
    "Line Paid",
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


class FootywireDataImporter:
    """Get data from footywire.com.au by scraping page or reading saved CSV"""

    def __init__(
        self,
        csv_dir: str = DATA_DIR,
        fixture_filename: str = "ft_match_list",
        betting_filename: str = "afl_betting",
    ) -> None:
        self.csv_dir = csv_dir
        self.fixture_filename = fixture_filename
        self.betting_filename = betting_filename

    def get_fixture(
        self, year_range: Optional[Tuple[int, int]] = None, fetch_data: bool = False
    ) -> pd.DataFrame:
        """
        Get AFL fixtures for given year range.

        Returns pandas.DataFrame with columns:
            date, venue, crowd, round, season, round_label, home_team, away_team,
            home_score, away_score
        """

        if fetch_data:
            return self.__clean_fixture_data_frame(
                self.__fetch_data(FIXTURE_PATH, year_range)
            )

        return self.__read_data_csv(self.fixture_filename, year_range)

    def get_betting_odds(
        self, year_range: Optional[Tuple[int, int]] = None, fetch_data: bool = False
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
            return self.__fetch_data(BETTING_PATH, year_range).pipe(
                self.__clean_betting_data_frame
            )

        return self.__read_data_csv(self.betting_filename, year_range)

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

    def __fetch_data(
        self, url_path: str, year_range: Optional[Tuple[int, int]]
    ) -> pd.DataFrame:
        this_year = date.today().year
        requested_year_range = year_range or (0, this_year + 1)
        yearly_data = []

        # Counting backwards to make sure we get all available years when year_range
        # is None
        for year in reversed(range(*requested_year_range)):
            year_data = self.__fetch_year(url_path, year)

            if year_data is None:
                # Depending on the month, there might not be betting data for the current year
                # yet, so keep going if the first result is blank
                if year == this_year:
                    continue

                break

            yearly_data.append(year_data)

        # Too many nested arrays to make using any() practical
        if len(yearly_data) == 0:  # pylint: disable=C1801
            raise ValueError(
                f"No data was found for the year range: {requested_year_range}"
            )

        data = list(itertools.chain.from_iterable(yearly_data))
        columns = FIXTURE_COLS if url_path == FIXTURE_PATH else BETTING_COLS

        return pd.DataFrame(data, columns=columns)

    def __fetch_year(self, url_path: str, year: int) -> Optional[np.ndarray]:
        res = requests.get(urljoin(FOOTY_WIRE_DOMAIN, url_path), params={"year": year})
        # Have to use html5lib, because default HTML parser wasn't working for this site
        soup = BeautifulSoup(res.text, "html5lib")

        if url_path == FIXTURE_PATH:
            return self.__get_fixture_data(soup, year)

        if url_path == BETTING_PATH:
            return self.__get_betting_data(soup, year)

        raise ValueError(f"Unknown path: {url_path}")

    def __get_betting_data(
        self, soup: BeautifulSoup, year: int
    ) -> Optional[np.ndarray]:
        # afl_betting page nests the data table inside of multiple outer tables
        table_rows = soup.select("form table table table tr")

        if not any(table_rows):
            return None

        are_round_labels = [any(row.select(".tbtitle")) for row in table_rows]
        round_groups = self.__group_by_round(table_rows, are_round_labels)

        # Due to some elements using rowspan to cover multiple rows, we need to get the
        # max length of all rows, then pad the shorter rows and forward fill the values
        max_len = max(
            [len(tr.find_all("td")) for tr in table_rows if any(tr.select(".data"))]
        )

        grouped_data = [
            self.__betting_data(year, max_len, round_group)
            for round_group in round_groups
        ]

        return list(itertools.chain.from_iterable(grouped_data))

    def __betting_data(
        self, year: int, max_len: int, round_group: List[element.Tag]
    ) -> np.ndarray:
        round_label = next(round_group[0].stripped_strings)
        round_rows = [
            self.__betting_row(max_len, row)
            for row in round_group
            if any(row.select(".data"))
        ]
        row_count = len(round_rows)
        round_label_column = np.repeat(round_label, row_count).reshape(-1, 1)
        season_column = np.repeat(year, row_count).reshape(-1, 1)

        return np.concatenate([round_rows, round_label_column, season_column], axis=1)

    def __get_fixture_data(self, soup: BeautifulSoup, year: int) -> np.ndarray:
        # CSS selector for elements with round labels and all table data
        data_html = soup.select(".tbtitle,.data")

        if not any(data_html):
            return None

        are_round_labels = [
            "tbtitle" in html_element.get("class") for html_element in data_html
        ]
        round_groups = self.__group_by_round(data_html, are_round_labels)

        grouped_data = [
            self.__fixture_data(year, round_group) for round_group in round_groups
        ]

        return list(itertools.chain.from_iterable(grouped_data))

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

        if any(valid_data_frame["Result"]):
            score_data_frame = (
                valid_data_frame["Result"]
                .str.split(RESULT_SEPARATOR, expand=True)
                .rename(columns={0: "home_score", 1: "away_score"})
                # For unplayed matches we convert scores to numeric, filling the resulting
                # NaNs with 0
                .pipe(
                    self.__convert_string_cols_to_numeric(["home_score", "away_score"])
                )
                .fillna(0)
            )
        # If there are no played matches in the retrieved data, we need to create
        # the score columns manually
        else:
            score_col = np.repeat(0, len(valid_data_frame))
            score_data_frame = pd.DataFrame(
                {"home_score": score_col, "away_score": score_col},
                index=valid_data_frame.index,
            )

        cleaned_data_frame = (
            valid_data_frame.drop(["Home v Away Teams", "Result"], axis=1)
            .rename(columns=lambda col: col.lower().replace(" ", "_"))
            .assign(
                date=self.__parse_dates,
                # Labelling round strings as 'round_label' and round numbers as 'round'
                # for consistency with fitzRoy column labels.
                round_label=lambda df: df["round"],
                round=self.__round_number,
            )
            .pipe(self.__convert_string_cols_to_numeric(["crowd"]))
            .astype({"season": int})
        )

        return (
            pd.concat([cleaned_data_frame, team_data_frame, score_data_frame], axis=1)
            .reset_index(drop=True)
            .sort_values("date")
        )

    def __clean_betting_data_frame(self, data_frame: pd.DataFrame) -> pd.DataFrame:
        cleaned_data_frame = (
            data_frame.drop(["colon", "redundant_line_paid"], axis=1)
            .rename(columns=lambda col: col.lower().replace(" ", "_"))
            .ffill()
            .assign(
                date=self.__parse_dates,
                round_label=lambda df: df["round"],
                round=self.__round_number,
            )
            .pipe(
                self.__convert_string_cols_to_numeric(
                    ["score", "margin", "win_paid", "line_paid"]
                )
            )
        )

        merged_df = (
            self.__split_home_away(cleaned_data_frame, "home")
            .merge(
                self.__split_home_away(cleaned_data_frame, "away"),
                on=BETTING_MATCH_COLS,
            )
            .drop_duplicates(
                subset=["home_team", "away_team", "season", "round_label"], keep="last"
            )
            .astype(
                {
                    "home_win_odds": float,
                    "home_line_odds": float,
                    "away_win_odds": float,
                    "away_line_odds": float,
                    "home_score": float,
                    "away_score": float,
                }
            )
        )

        sorted_cols = BETTING_MATCH_COLS + [
            col for col in merged_df.columns if col not in BETTING_MATCH_COLS
        ]

        return merged_df[sorted_cols]

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
    def __convert_string_cols_to_numeric(cols_to_convert: List[str]) -> pd.DataFrame:
        converted_column_assignments = {
            col_name: lambda df, col=col_name: pd.to_numeric(
                df[col], errors="coerce"
            ).fillna(0)
            for col_name in cols_to_convert
        }

        return lambda df: df.assign(**converted_column_assignments)

    @staticmethod
    def __betting_row(max_len: int, tr: element.Tag) -> List[Optional[str]]:
        # Can't used stripped_strings method on tr, because it removes blank <td>
        # elements (e.g. 'Margin' column before a match is played), resulting in row
        # values not matching column labels
        table_row_strings = [td.get_text(strip=True) for td in tr.find_all("td")]
        padding = [None] * (max_len - len(table_row_strings))

        return list(itertools.chain.from_iterable([padding, table_row_strings]))

    @staticmethod
    def __group_by_round(
        data_html: List[element.Tag], are_round_labels: List[bool]
    ) -> List[List[element.Tag]]:
        round_row_indices = np.argwhere(are_round_labels).flatten()
        round_groups = []

        for idx, lower_bound in enumerate(round_row_indices):
            if idx + 1 < len(round_row_indices):
                round_groups.append(data_html[lower_bound : round_row_indices[idx + 1]])
            else:
                round_groups.append(data_html[lower_bound:])

        return round_groups

    @staticmethod
    def __fixture_data(year: int, round_group: List[element.Tag]) -> np.ndarray:
        round_label = next(round_group[0].stripped_strings)
        round_strings = [
            # Some data elements break up the interior text with interior html elements,
            # meaning the text is sometimes broken up, resulting in multiple stripped
            # strings per element
            " ".join(list(html_element.stripped_strings))
            for html_element in round_group[1:]
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
    def __parse_dates(data_frame: pd.DataFrame) -> pd.Series:
        # Betting dates aren't displayed with years on the page, so we have to add them
        return pd.to_datetime(
            data_frame["date"] + " " + data_frame["season"].astype(int).astype(str)
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
