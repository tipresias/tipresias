from typing import List
import pandas as pd

from machine_learning.types import DataFrameTransformer
from machine_learning.data_config import INDEX_COLS
from machine_learning.utils import DataTransformerMixin


class FeatureBuilder(DataTransformerMixin):
    """Add features to data frames.

    Args:
        feature_funcs (iterable): Iterable containing instances of Feature.

    Attributes:
        feature_funcs (iterable): Iterable containing instances of Feature.
    """

    def __init__(
        self,
        index_cols: List[str] = INDEX_COLS,
        feature_funcs: List[DataFrameTransformer] = [],
    ) -> None:
        self.index_cols = index_cols
        self._data_transformers = feature_funcs

    def transform(self, data_frame: pd.DataFrame) -> pd.DataFrame:
        """Add new features to the given data frame."""

        required_column_set = set(self.index_cols)
        data_frame_column_set = set(data_frame.columns)

        if (
            required_column_set.intersection(data_frame_column_set)
            != required_column_set
        ):
            raise ValueError(
                "To calculate new features, all required columns must be in the "
                "data frame.\n"
                f"Required columns: {required_column_set}"
                f"Columns given: {data_frame_column_set}"
            )

        return self._compose_transformers(  # pylint: disable=E1102
            data_frame.copy()
            .set_index(self.index_cols, drop=False)
            .rename_axis([None] * len(self.index_cols))
            .sort_index()
        )

    @property
    def data_transformers(self) -> List[DataFrameTransformer]:
        return self._data_transformers

    @staticmethod
    def __compose_two(
        composed_func: DataFrameTransformer, func_element: DataFrameTransformer
    ) -> DataFrameTransformer:
        return lambda x: composed_func(func_element(x))
