from typing import List, Dict, Union, Tuple
from functools import partial
import pandas as pd
import numpy as np

from machine_learning.data_config import INDEX_COLS

STATS_COLS = [
    "rolling_prev_match_kicks",
    "rolling_prev_match_marks",
    "rolling_prev_match_handballs",
    "rolling_prev_match_goals",
    "rolling_prev_match_behinds",
    "rolling_prev_match_hit_outs",
    "rolling_prev_match_tackles",
    "rolling_prev_match_rebounds",
    "rolling_prev_match_inside_50s",
    "rolling_prev_match_clearances",
    "rolling_prev_match_clangers",
    "rolling_prev_match_frees_for",
    "rolling_prev_match_frees_against",
    "rolling_prev_match_contested_possessions",
    "rolling_prev_match_uncontested_possessions",
    "rolling_prev_match_contested_marks",
    "rolling_prev_match_marks_inside_50",
    "rolling_prev_match_one_percenters",
    "rolling_prev_match_bounces",
    "rolling_prev_match_goal_assists",
    "rolling_prev_match_time_on_ground",
    "last_year_brownlow_votes",
]

REQUIRED_COLS = ["oppo_team", "player_id", "player_name", "date"] + STATS_COLS


class PlayerDataAggregator:
    """Perform aggregations to turn player-match data into team-match data."""

    def __init__(
        self, index_cols: List[str] = INDEX_COLS, aggregations: List[str] = ["sum"]
    ) -> None:
        self.index_cols = index_cols
        self.aggregations = aggregations

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

            raise ValueError(
                f"All required columns ({required_cols}) must be in the data frame, "
                "but the given data frame has the following columns: "
                f"{list(data_frame.columns)}.\n\nMissing columns: "
                f"{missing_cols}"
            )

        match_stats_cols = [
            col
            for col in data_frame.select_dtypes("number")
            # Excluding player stats columns & index columns, which are included in the
            # groupby index and readded to the dataframe later
            if col not in STATS_COLS + self.index_cols
        ]

        agg_data_frame = (
            data_frame.drop(["player_id", "player_name"], axis=1)
            # Adding some non-index columns in the groupby, because it doesn't change
            # the grouping and makes it easier to keep for the final data frame.
            .groupby(self.index_cols + ["oppo_team", "date"]).aggregate(
                self.__aggregations(match_stats_cols)
            )
        )

        agg_column_name = partial(self.__agg_column_name, match_stats_cols)

        agg_data_frame.columns = [
            agg_column_name(column_pair)
            for column_pair in agg_data_frame.columns.values
        ]

        # Various finals matches have been draws and replayed,
        # and sometimes home/away is switched requiring us to drop duplicates
        # at the end.
        # This eliminates some matches from Round 15 in 1897, because they
        # played some sort of round-robin tournament for finals, but I'm
        # not too worried about the loss of that data.
        return (
            agg_data_frame.dropna()
            .reset_index()
            .sort_values("date")
            .drop_duplicates(subset=self.index_cols, keep="last")
            .astype({match_col: int for match_col in match_stats_cols})
            .set_index(self.index_cols, drop=False)
            .rename_axis([None] * len(self.index_cols))
            .sort_index()
        )

    def __aggregations(
        self, match_stats_cols: List[str]
    ) -> Dict[str, Union[str, List[str]]]:
        player_aggs = {col: self.aggregations for col in STATS_COLS}
        # Since match stats are the same across player rows, taking the mean
        # is the easiest way to aggregate them
        match_aggs = {col: "mean" for col in match_stats_cols}

        return {**player_aggs, **match_aggs}

    @staticmethod
    def __agg_column_name(
        match_stats_cols: List[str], column_pair: Tuple[str, str]
    ) -> str:
        column_label, _ = column_pair
        return (
            column_label if column_label in match_stats_cols else "_".join(column_pair)
        )
