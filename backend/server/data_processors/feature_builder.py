from typing import List, Sequence
from functools import reduce, partial
import pandas as pd

from server.types import FeatureFunctionType

INDEX_COLS: List[str] = ["team", "year", "round_number"]
REQUIRED_COLS: List[str] = INDEX_COLS + ["oppo_team"]


class FeatureBuilder:
    """Add features to data frames.

    Args:
        feature_funcs (iterable): Iterable containing instances of Feature.

    Attributes:
        feature_funcs (iterable): Iterable containing instances of Feature.
    """

    def __init__(
        self,
        index_cols: List[str] = INDEX_COLS,
        feature_funcs: Sequence[FeatureFunctionType] = [],
    ) -> None:
        self.index_cols = index_cols
        self.feature_funcs = [
            partial(self.__add_feature, feature_func) for feature_func in feature_funcs
        ]
        self._compose_all = reduce(
            self.__compose_two, reversed(self.feature_funcs), lambda x: x
        )

    def transform(self, data_frame: pd.DataFrame) -> pd.DataFrame:
        """Add new features to the given data frame."""

        required_cols = REQUIRED_COLS + self.index_cols

        if any((req_col not in data_frame.columns for req_col in required_cols)):
            raise ValueError(
                "To calculate opposition column, all required columns "
                f"({required_cols}) must be in data frame, "
                f"but the columns given were {data_frame.columns}"
            )

        return self._compose_all(
            data_frame.copy().set_index(self.index_cols, drop=False).sort_index()
        )

    @staticmethod
    def __add_feature(
        feature_func: FeatureFunctionType, data_frame: pd.DataFrame
    ) -> pd.DataFrame:
        """Use the given feature function to add the feature and opposition team feature
        to the data frame"""

        return feature_func(data_frame)

    @staticmethod
    def __compose_two(
        composed_func: FeatureFunctionType, func_element: FeatureFunctionType
    ) -> FeatureFunctionType:
        return lambda x: composed_func(func_element(x))
