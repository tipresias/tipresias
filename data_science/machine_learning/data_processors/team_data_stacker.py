from typing import List, Callable
import pandas as pd
import numpy as np

from machine_learning.data_config import INDEX_COLS

REQUIRED_COLS: List[str] = ["home_team", "year", "round_number"]


class TeamDataStacker:
    """Reorganise data from match rows to team-match rows.

    Args:
        index_cols (list): Column names to be used as a multi-index.

    Attributes:
        index_cols (list): Column names to be used as a multi-index.
    """

    def __init__(self, index_cols: List[str] = INDEX_COLS) -> None:
        self.index_cols = index_cols

    def transform(self, data_frame: pd.DataFrame) -> pd.DataFrame:
        """Stack home & away team data, and add 'oppo_' team columns.

        Args:
            data_frame (pandas.DataFrame): Data frame to be transformed.

        Returns:
            pandas.DataFrame
        """

        if any((req_col not in data_frame.columns for req_col in REQUIRED_COLS)):
            raise ValueError(
                f"All required columns ({REQUIRED_COLS}) must be in the data frame, "
                "but the given data frame has the following columns: "
                f"{data_frame.columns}"
            )

        team_dfs = [
            self.__team_df(data_frame, "home"),
            self.__team_df(data_frame, "away"),
        ]

        return (
            pd.concat(team_dfs, join="inner")
            .sort_values("date", ascending=True)
            # Various finals matches have been draws and replayed,
            # and sometimes home/away is switched requiring us to drop duplicates
            # at the end.
            # This eliminates some matches from Round 15 in 1897, because they
            # played some sort of round-robin tournament for finals, but I'm
            # not too worried about the loss of that data.
            .drop_duplicates(subset=self.index_cols, keep="last")
            .sort_index()
        )

    def __team_df(self, data_frame: pd.DataFrame, team_type: str) -> pd.DataFrame:
        is_at_home = team_type == "home"

        if is_at_home:
            oppo_team_type = "away"
            at_home_col = np.ones(len(data_frame))
        else:
            oppo_team_type = "home"
            at_home_col = np.zeros(len(data_frame))

        return (
            data_frame.rename(
                columns=self.__replace_col_names(team_type, oppo_team_type)
            )
            .assign(at_home=at_home_col)
            .set_index(self.index_cols, drop=False)
            .rename_axis([None] * len(self.index_cols))
        )

    @staticmethod
    def __replace_col_names(
        team_type: str, oppo_team_type: str
    ) -> Callable[[str], str]:
        return lambda col_name: (
            col_name.replace(f"{team_type}_", "").replace(f"{oppo_team_type}_", "oppo_")
        )
