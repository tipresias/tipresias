from typing import List, Optional
import pandas as pd

from machine_learning.data_config import INDEX_COLS

REQUIRED_COLS: List[str] = INDEX_COLS + ["oppo_team"]


class OppoFeatureBuilder:
    """Add opposition team features to data frames.

    Args:
        match_cols (list): List of column names for columns to not convert to 'oppo'
            columns. All unlisted columns will be converted. Can't coexist
            with oppo_feature_cols.
        oppo_feature_cols (list): List of column names for columns to convert to 'oppo'
            columns, then add to the data frame. Can't coexist with match_cols.

    Attributes:
        match_cols (list): List of column names for columns to not convert to 'oppo'
            columns. All unlisted columns will be converted.
        oppo_feature_cols (list): List of column names for columns to convert to 'oppo'
            columns, then add to the data frame.
    """

    def __init__(
        self, match_cols: List[str] = [], oppo_feature_cols: List[str] = []
    ) -> None:
        if any(match_cols) and any(oppo_feature_cols):
            raise ValueError(
                "To avoid conflicts, you can't include both match_cols "
                "and oppo_feature_cols. Choose the shorter list to determine which "
                "columns to skip and which to turn into opposition features."
            )

        self.oppo_feature_cols = oppo_feature_cols
        self.match_cols = match_cols

    def transform(self, data_frame: pd.DataFrame) -> pd.DataFrame:
        """Add new opposition features to the given data frame."""

        required_cols = REQUIRED_COLS + self.__cols_to_convert(data_frame)

        if any((req_col not in data_frame.columns for req_col in required_cols)):
            raise ValueError(
                "To calculate opposition column, all required columns "
                f"({required_cols}) must be in data frame, "
                f"but the columns given were {data_frame.columns}"
            )

        transform_data_frame = (
            data_frame.copy()
            .set_index(INDEX_COLS, drop=False)
            .rename_axis([None] * len(INDEX_COLS))
            .sort_index()
        )

        concated_data_frame = pd.concat(
            [transform_data_frame, self.__oppo_features(transform_data_frame)], axis=1
        )

        are_duplicate_columns = concated_data_frame.columns.duplicated()
        if are_duplicate_columns.any():
            raise ValueError(
                "The data frame with 'oppo' features added has duplicate columns."
                "The offending columns are: "
                f"{concated_data_frame.columns[are_duplicate_columns]}"
            )

        return concated_data_frame

    def __cols_to_convert(self, data_frame: pd.DataFrame) -> List[str]:
        if any(self.oppo_feature_cols):
            return self.oppo_feature_cols

        return [col for col in data_frame.columns if col not in self.match_cols]

    def __oppo_features(self, data_frame: pd.DataFrame) -> Optional[pd.DataFrame]:
        """Add the same features, but for the current opposition team"""

        cols_to_convert = self.__cols_to_convert(data_frame)

        if not any(cols_to_convert):
            return None

        oppo_cols = {col_name: f"oppo_{col_name}" for col_name in cols_to_convert}
        oppo_col_names = oppo_cols.values()
        column_translations = {**{"oppo_team": "team"}, **oppo_cols}

        return (
            data_frame.reset_index(drop=True)
            .loc[:, ["year", "round_number", "oppo_team"] + list(cols_to_convert)]
            # We switch out oppo_team for team in the index,
            # then assign feature as oppo_{feature_column}
            .rename(columns=column_translations)
            .set_index(INDEX_COLS)
            .sort_index()
            .loc[:, list(oppo_col_names)]
        )
