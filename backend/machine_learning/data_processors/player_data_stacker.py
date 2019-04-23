from typing import List, Callable
import pandas as pd

REQUIRED_COLS: List[str] = [
    "playing_for",
    "home_team",
    "away_team",
    "home_score",
    "away_score",
    "match_id",
]


class PlayerDataStacker:
    """Reorganise data from player match rows to team match rows."""

    def transform(self, data_frame: pd.DataFrame) -> pd.DataFrame:
        """Stack home & away player data, and add 'oppo_' team columns.

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

        return pd.concat(team_dfs, sort=True).drop(["match_id", "playing_for"], axis=1)

    def __team_df(self, data_frame: pd.DataFrame, team_type: str) -> pd.DataFrame:
        return (
            data_frame[data_frame["playing_for"] == data_frame[f"{team_type}_team"]]
            .rename(columns=self.__replace_col_names(team_type))
            .assign(at_home=1 if team_type == "home" else 0)
            .pipe(self.__sort_columns)
        )

    @staticmethod
    def __replace_col_names(team_type: str) -> Callable[[str], str]:
        oppo_team_type = "away" if team_type == "home" else "home"

        return lambda col_name: (
            col_name.replace(f"{team_type}_", "").replace(f"{oppo_team_type}_", "oppo_")
        )

    @staticmethod
    def __sort_columns(data_frame: pd.DataFrame) -> pd.DataFrame:
        return data_frame[data_frame.columns.sort_values()]
