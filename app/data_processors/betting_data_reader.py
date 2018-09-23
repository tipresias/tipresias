import os
import pandas as pd

project_path = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '../../'))


class BettingDataReader():
    def __init__(self, index_col=('date', 'venue'),
                 parse_dates=['date']):
        self.index_col = index_col
        self.parse_dates = parse_dates

    def transform(self, filename='afl_betting.csv'):
        data_frame = pd.read_csv(f'{project_path}/data/{filename}',
                                 index_col=self.index_col,
                                 parse_dates=self.parse_dates)

        home_df = self.__split_home_away(data_frame, 'home')
        away_df = self.__split_home_away(data_frame, 'away')

        return home_df.merge(away_df, on=self.index_col).reset_index()

    def __split_home_away(self, data_frame, team_type):
        return (data_frame[data_frame['home'] == int(team_type == 'home')]
                .drop('home', axis=1)
                .rename(columns=self.__rename_columns(team_type)))

    def __rename_columns(self, team_type):
        return lambda column: f'{team_type}_{column}'
