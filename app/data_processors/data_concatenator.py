from functools import reduce
import numpy as np
import pandas as pd


class DataConcatenator():
    def __init__(self, drop_cols=['date']):
        self.drop_cols = drop_cols

    def transform(self, data_frames):
        all_columns = np.concatenate(
            [data_frame.columns for data_frame in data_frames]
        )

        for drop_col in self.drop_cols:
            if drop_col not in all_columns:
                raise ValueError(f'All drop_cols must be in at least one of the given data frames, '
                                 'but {drop_col} is not in {all_columns}')

        shared_columns = reduce(np.intersect1d,
                                (data_frame.columns for data_frame in data_frames))

        if len(shared_columns) == 0:
            raise ValueError('The data frames do not have any columns in common '
                             'and cannot be concatenated.')

        reindexed_data_frames = [
            data_frame.set_index(list(shared_columns)) for data_frame in data_frames
        ]

        return (pd.concat(reindexed_data_frames, axis=1)
                  .dropna()
                  .reset_index()
                  .drop(self.drop_cols, axis=1))
