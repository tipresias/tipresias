from typing import List, Dict
import pandas as pd
import numpy as np

INDEX_COLS: List[str] = ['team', 'year', 'round_number']
STATS_COLS = ['rolling_prev_match_kicks', 'rolling_prev_match_marks',
              'rolling_prev_match_handballs', 'rolling_prev_match_goals',
              'rolling_prev_match_behinds', 'rolling_prev_match_hit_outs',
              'rolling_prev_match_tackles', 'rolling_prev_match_rebounds',
              'rolling_prev_match_inside_50s', 'rolling_prev_match_clearances',
              'rolling_prev_match_clangers', 'rolling_prev_match_frees_for',
              'rolling_prev_match_frees_against',
              'rolling_prev_match_contested_possessions',
              'rolling_prev_match_uncontested_possessions',
              'rolling_prev_match_contested_marks',
              'rolling_prev_match_marks_inside_50',
              'rolling_prev_match_one_percenters', 'rolling_prev_match_bounces',
              'rolling_prev_match_goal_assists', 'rolling_prev_match_time_on_ground',
              'last_year_brownlow_votes']
MATCH_STATS_COLS = ['at_home', 'score', 'oppo_score']
REQUIRED_COLS = (['oppo_team', 'player_id', 'player_name'] +
                 STATS_COLS +
                 MATCH_STATS_COLS)


class PlayerDataAggregator():
    """Perform aggregations to turn player-match data into team-match data

    Args:
        index_cols (list): Column names to be used as a multi-index.

    Attributes:
        index_cols (list): Column names to be used as a multi-index.
    """

    def __init__(self, index_cols: List[str] = INDEX_COLS) -> None:
        self.index_cols = index_cols

    def transform(self, data_frame: pd.DataFrame) -> pd.DataFrame:
        """Aggregate player stats by team.

        Args:
            data_frame (pandas.DataFrame): Data frame to be transformed.

        Returns:
            pandas.DataFrame
        """

        required_cols = REQUIRED_COLS + self.index_cols

        if any((req_col not in data_frame.columns for req_col in required_cols)):

            missing_cols = np.setdiff1d(required_cols, data_frame.columns)

            raise ValueError(f'All required columns ({required_cols}) must be in the data frame, '
                             'but the given data frame has the following columns: '
                             f'{list(data_frame.columns)}.\n\nMissing columns: '
                             f'{missing_cols}')

        return (data_frame
                .drop(['player_id', 'player_name'], axis=1)
                # 'oppo_team' isn't an index column, but including it in the groupby
                # doesn't change the grouping and makes it easier to keep for the final
                # data frame.
                .groupby(self.index_cols + ['oppo_team'])
                .aggregate(self.__aggregations())
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

    @staticmethod
    def __aggregations() -> Dict[str, str]:
        player_aggs = {col: 'sum' for col in STATS_COLS}
        # Since match stats are the same across player rows, taking the mean
        # is the easiest way to aggregate them
        match_aggs = {col: 'mean' for col in MATCH_STATS_COLS}

        return {**player_aggs, **match_aggs}
