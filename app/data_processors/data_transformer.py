import pandas as pd
import numpy as np

INDEX_COLS = ['team', 'year', 'round_number']


class DataTransformer():
    def __init__(self, index_cols=INDEX_COLS):
        self.index_cols = index_cols

    def transform(self, data_frame):
        if any((req_col not in data_frame.columns for req_col in ['home_team', 'year', 'round_number'])):
            raise ValueError(f'All index columns {self.index_cols} must be in the data frame, '
                             f'but the given data frame has the following columns: {data_frame.columns}')

        team_dfs = [self.__team_df(data_frame, 'home'),
                    self.__team_df(data_frame, 'away')]

        return pd.concat(team_dfs, join='inner').sort_index()

    def __team_df(self, data_frame, team_type):
        is_at_home = team_type == 'home'

        if is_at_home:
            oppo_team_type = 'away'
            at_home_col = np.ones(len(data_frame))
        else:
            oppo_team_type = 'home'
            at_home_col = np.zeros(len(data_frame))

        return (data_frame.rename(columns=self.__replace_col_names(team_type, oppo_team_type))
                .assign(at_home=at_home_col)
                .set_index(self.index_cols, drop=False)
                # Gotta drop duplicates, because St Kilda & Carlton tied a Grand Final
                # in 2010 and had to replay it, so let's just pretend that never happened
                .drop_duplicates(subset=self.index_cols, keep='last'))

    def __replace_col_names(self, team_type, oppo_team_type):
        return lambda col_name: (col_name.replace(f'{team_type}_', '')
                                         .replace(f'{oppo_team_type}_', 'oppo_'))
