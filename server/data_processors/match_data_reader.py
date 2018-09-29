import os
import pandas as pd

PROJECT_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '../../')
)


class MatchDataReader():
    """Read betting data from csv and turn into data frame.

    Args:
        parse_dates (boolean, list): Column to try to parse into dates for data frame.
            See pandas.read_csv().

    Attributes:
        parse_dates (boolean, list): Column to try to parse into dates for data frame.
            See pandas.read_csv().
    """

    def __init__(self, parse_dates=['date']):
        self.parse_dates = parse_dates

    def transform(self, filename='ft_match_list.csv'):
        """Transform a csv file into a data frame.

        Args:
            filename (string): Name of the csv file.

        Returns:
            pandas.DataFrame
        """

        return (pd.read_csv(f'{PROJECT_PATH}/data/{filename}', parse_dates=self.parse_dates)
                .rename(columns={'date': 'datetime'})
                .assign(date=self.__convert_datetime_to_date))

    @staticmethod
    def __convert_datetime_to_date(data_frame):
        return data_frame['datetime'].map(lambda date_time: date_time.date())
