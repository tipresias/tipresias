"""Module for the BettingDataReader class"""

from typing import Tuple, List, Callable
import pandas as pd

from project.settings.common import DATA_DIR


class BettingDataReader:
    """Read betting data from csv and turn into data frame.

    Args:
        index_col (int, iterable): Column label(s) to use as index(es) for data frame.
            See pandas.read_csv().
        parse_dates (boolean, list): Column to try to parse into dates for data frame.
            See pandas.read_csv().

    Attributes:
        index_col (int, iterable): Column label(s) to use as index(es) for data frame.
            See pandas.read_csv().
        parse_dates (boolean, list): Column to try to parse into dates for data frame.
            See pandas.read_csv().
    """

    def __init__(
        self,
        index_col: Tuple[str, str] = ("date", "venue"),
        parse_dates: List[str] = ["date"],
    ) -> None:
        self.index_col = index_col
        self.parse_dates = parse_dates

    def transform(self, filename: str = "afl_betting.csv") -> pd.DataFrame:
        """Transform a csv file into a data frame.

        Args:
            filename (string): Name of the csv file.

        Returns:
            pandas.DataFrame
        """

        data_frame = pd.read_csv(
            f"{DATA_DIR}/{filename}",
            index_col=self.index_col,
            parse_dates=self.parse_dates,
        )

        home_df = self.__split_home_away(data_frame, "home")
        away_df = self.__split_home_away(data_frame, "away")

        return home_df.merge(away_df, on=self.index_col).reset_index()

    def __split_home_away(
        self, data_frame: pd.DataFrame, team_type: str
    ) -> pd.DataFrame:
        return (
            data_frame[data_frame["home"] == int(team_type == "home")]
            .drop("home", axis=1)
            .rename(columns=self.__rename_columns(team_type))
        )

    @staticmethod
    def __rename_columns(team_type: str) -> Callable[[str], str]:
        return lambda column: f"{team_type}_{column}"
