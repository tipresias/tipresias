"""For reading match data from a CSV"""

from typing import List
import pandas as pd

from project.settings.common import DATA_DIR


class MatchDataReader:
    """Read betting data from csv and turn into data frame.

    Args:
        parse_dates (boolean, list): Column to try to parse into dates for data frame.
            See pandas.read_csv().

    Attributes:
        parse_dates (boolean, list): Column to try to parse into dates for data frame.
            See pandas.read_csv().
    """

    def __init__(self, parse_dates: List[str] = ["date"]) -> None:
        self.parse_dates = parse_dates

    def transform(self, filename: str = "ft_match_list.csv") -> pd.DataFrame:
        """Transform a csv file into a data frame.

        Args:
            filename (string): Name of the csv file.

        Returns:
            pandas.DataFrame
        """

        return (
            pd.read_csv(f"{DATA_DIR}/{filename}", parse_dates=self.parse_dates)
            .rename(columns={"date": "datetime"})
            .assign(date=self.__convert_datetime_to_date)
        )

    @staticmethod
    def __convert_datetime_to_date(data_frame: pd.DataFrame) -> pd.Series:
        return data_frame["datetime"].map(lambda date_time: date_time.date())
