from typing import List, Callable
import pandas as pd
import numpy as np

INDEX_COLS: List[str] = ['team', 'year', 'round_number']
STATS_COLS = ['kicks', 'marks', 'handballs', 'goals', 'behinds', 'hit_outs', 'tackles',
              'rebounds', 'inside_50s', 'clearances', 'clangers', 'frees_for',
              'frees_against', 'contested_possessions', 'uncontested_possessions',
              'contested_marks', 'marks_inside_50', 'one_percenters',
              'bounces', 'goal_assists', 'time_on_ground', 'last_year_brownlow_votes']
MATCH_STATS_COLS = ['at_home', 'score', 'oppo_score']
REQUIRED_COLS: List[str] = [
    'playing_for', 'year', 'round_number', 'home_team', 'away_team', 'home_score',
    'away_score', 'player_id', 'player_name', 'match_id'
] + STATS_COLS


class PlayerDataStacker():
    """Reorganise data from player match rows to team match rows.

    Args:
        index_cols (list): Column names to be used as a multi-index.

    Attributes:
        index_cols (list): Column names to be used as a multi-index.
    """

    def __init__(self, index_cols: List[str] = INDEX_COLS) -> None:
        self.index_cols = index_cols

    def transform(self, data_frame: pd.DataFrame) -> pd.DataFrame:
        """Stack home & away player data, and add 'oppo_' team columns.

        Args:
            data_frame (pandas.DataFrame): Data frame to be transformed.

        Returns:
            pandas.DataFrame
        """

        if any((req_col not in data_frame.columns for req_col in REQUIRED_COLS)):
            raise ValueError(f'All required columns ({REQUIRED_COLS}) must be in the data frame, '
                             'but the given data frame has the following columns: '
                             f'{data_frame.columns}')

        player_aggs = {
            col: 'sum' for col in STATS_COLS
        }
        # Since match stats are the same across player rows, taking the mean
        # is the easiest way to aggregate them
        match_aggs = {col: 'mean' for col in MATCH_STATS_COLS}

        aggregations = {**player_aggs, **match_aggs}

        team_dfs = [self.__team_df(data_frame, 'home'),
                    self.__team_df(data_frame, 'away')]

        return (pd.concat(team_dfs, sort=True)
                .drop(['player_id', 'player_name', 'match_id', 'playing_for'], axis=1)
                # 'oppo_team' isn't an index column, but including it in the groupby
                # doesn't change the grouping and makes it easier to keep for the final
                # data frame.
                .groupby(self.index_cols + ['oppo_team'])
                .aggregate(aggregations)
                .reset_index()
                # Various finals matches have been draws and replayed,
                # and sometimes home/away is switched requiring us to drop duplicates
                # at the end.
                # This eliminates some matches from Round 15 in 1897, because they
                # played some sort of round-robin tournament for finals, but I'm
                # not too worried about the loss of that data.
                .drop_duplicates(subset=self.index_cols, keep='last')
                .astype({
                    match_col: int for match_col in MATCH_STATS_COLS + ['year', 'round_number']
                })
                .set_index(self.index_cols, drop=False)
                .sort_index())

    def __team_df(self, data_frame: pd.DataFrame, team_type: str) -> pd.DataFrame:
        return self.__sort_columns(
            data_frame
            [data_frame['playering_for'] == data_frame[f'{team_type}_team']]
            .rename(columns=self.__replace_col_names(team_type))
            .assign(at_home=1 if team_type == 'home' else 0)
        )

    @staticmethod
    def __replace_col_names(team_type: str) -> Callable[[str], str]:
        oppo_team_type = 'away' if team_type == 'home' else 'home'

        return lambda col_name: (col_name
                                 .replace(f'{team_type}_', '')
                                 .replace(f'{oppo_team_type}_', 'oppo_'))

    @staticmethod
    def __sort_columns(data_frame: pd.DataFrame) -> pd.DataFrame:
        return data_frame[data_frame.columns.sort_values()]
