import os
import pandas as pd

project_path = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '../../'))


class MatchDataReader():
    def __init__(self, parse_dates=['date']):
        self.parse_dates = parse_dates

    def transform(self, filename='ft_match_list.csv'):
        return (pd.read_csv(f'{project_path}/data/{filename}', parse_dates=self.parse_dates)
                .rename(columns={'date': 'datetime'})
                .assign(date=self.__convert_datetime_to_date))

    def __convert_datetime_to_date(self, df):
        return df['datetime'].map(lambda date_time: date_time.date())
