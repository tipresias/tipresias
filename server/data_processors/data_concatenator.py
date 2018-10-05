from typing import List
from functools import reduce
import numpy as np
import pandas as pd


class DataConcatenator():
    """Concatenate two data frames with shared columns

    Args:
        drop_cols (string, list): Column(s) to drop at the end of transformation.

    Attributes:
        drop_cols (string, list): Column(s) to drop at the end of transformation.
    """

    def __init__(self, drop_cols: List[str] = ['date']) -> None:
        self.drop_cols = drop_cols

    def transform(self, data_frames: pd.DataFrame) -> pd.DataFrame:
        """Concatenate the given data_frames

        Args:
            data_frames (iterable): Data frames to concatenate

        Returns:
            pd.DataFrame
        """

        shared_columns = reduce(np.intersect1d,
                                (data_frame.columns for data_frame in data_frames))

        if not any(shared_columns):
            raise ValueError('The data frames do not have any columns in common '
                             'and cannot be concatenated.')

        reindexed_data_frames = [
            data_frame.set_index(list(shared_columns)) for data_frame in data_frames
        ]

        return (pd
                .concat(reindexed_data_frames, axis=1)
                .dropna()
                .reset_index()
                .drop(self.drop_cols, axis=1))
