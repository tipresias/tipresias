import os
import sys
from functools import reduce, partial
import numpy as np

PROJECT_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '../../')
)

if PROJECT_PATH not in sys.path:
    sys.path.append(PROJECT_PATH)

from app.data_processors.feature_functions import (
    add_last_week_result,
    add_last_week_score,
    add_cum_percent,
    add_cum_win_points,
    add_rolling_pred_win_rate,
    add_rolling_last_week_win_rate,
    add_ladder_position,
    add_win_streak
)

INDEX_COLS = ['year', 'round_number', 'team']
REQUIRED_COLS = INDEX_COLS + ['oppo_team']
# This is just for convenience based on current needs; might remove it later
DEFAULT_FEATURES = [
    add_last_week_result,
    add_last_week_score,
    add_cum_percent,
    add_cum_win_points,
    add_rolling_pred_win_rate,
    add_rolling_last_week_win_rate,
    add_ladder_position,
    add_win_streak
]


class FeatureBuilder():
    """Add features to data frames.

    Args:
        new_features (iterable): Iterable containing instances of Feature.

    Attributes:
        new_features (iterable): Iterable containing instances of Feature.
    """

    def __init__(self, feature_funcs=DEFAULT_FEATURES):
        self.feature_funcs = [
            self.__build_feature_function(feature_func) for feature_func in feature_funcs
        ]
        self._compose_all = reduce(
            self.__compose_two, reversed(self.feature_funcs), lambda x: x
        )

    def transform(self, data_frame):
        """Add new features to the given data frame."""
        return self._compose_all(data_frame.copy())

    def __build_feature_function(self, feature_func):
        """Build a partial function function with the given feature function argument set"""
        return partial(self.__add_feature, feature_func)

    def __add_feature(self, feature_func, data_frame):
        """Use the given feature function to add the feature and opposition team feature
        to the data frame"""
        new_data_frame = feature_func(data_frame)
        new_feature_label = np.intersect1d(data_frame.columns,
                                           new_data_frame.columns)

        if any(new_feature_label):
            feature_label = new_feature_label[0]
            new_data_frame.loc[:, f'oppo_{feature_label}'] = self.__oppo_feature(data_frame,
                                                                                 feature_label)

        return new_data_frame

    @staticmethod
    def __compose_two(composed_func, func_element):
        return lambda x: composed_func(func_element(x))

    @staticmethod
    def __oppo_feature(data_frame, col_name):
        """Add the same feature, but for the current opposition team"""
        if any((req_col not in data_frame.columns for req_col in REQUIRED_COLS)):
            raise ValueError("To calculate opposition column, all required columns ({REQUIRED_COLS})"
                             f"must be in data frame columns, but the columns given are {data_frame.columns}")
        oppo_col = (data_frame
                    .loc[:, ['year', 'round_number', 'oppo_team', col_name]]
                    # We switch out oppo_team for team in the index,
                    # then assign feature as oppo_{feature_column}
                    .rename(columns={'oppo_team': 'team'})
                    .set_index(INDEX_COLS)
                    .sort_index())

        return oppo_col[col_name]
