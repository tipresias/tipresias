from typing import Tuple, List, Callable
from functools import partial
import itertools
import pandas as pd

from server.types import DataFrameTransformer
from server.ml_models.data_config import AVG_SEASON_LENGTH

DataFrameCalculator = Callable[[pd.DataFrame], pd.Series]
CalculatorPair = Tuple[Callable[[str], DataFrameCalculator], List[str]]

TEAM_LEVEL = 0


def _calculate_feature_col(
    data_calculator: Callable[[str], DataFrameCalculator], columns: List[str]
) -> List[DataFrameCalculator]:
    if len(columns) != len(set(columns)):
        raise ValueError(
            "Some column names are duplicated, which will result in duplicate data frame "
            "columns. Make sure each column is calculated once."
        )

    return [data_calculator(column) for column in columns]


def _calculate_features(calculators: List[CalculatorPair], data_frame: pd.DataFrame):
    calculator_func_lists = [
        _calculate_feature_col(calculator, columns)
        for calculator, columns in calculators
    ]
    calculator_funcs = list(itertools.chain.from_iterable(calculator_func_lists))
    calculated_cols = [calc_func(data_frame) for calc_func in calculator_funcs]

    return pd.concat([data_frame, *calculated_cols], axis=1)


def feature_calculator(calculators: List[CalculatorPair]) -> DataFrameTransformer:
    return partial(_calculate_features, calculators)


def _rolling_rate(column: str, data_frame: pd.DataFrame) -> pd.Series:
    if column not in data_frame.columns:
        raise ValueError(
            f"To calculate rolling rate, '{column}' "
            "must be in data frame, but the columns given were "
            f"{data_frame.columns}"
        )

    groups = data_frame[column].groupby(level=TEAM_LEVEL, group_keys=False)

    # Using mean season length (23) for rolling window due to a combination of
    # testing different window values for a previous model and finding 23 to be
    # a good window for data vis.
    # Not super scientific, but it works well enough.
    rolling_rate = groups.rolling(window=AVG_SEASON_LENGTH).mean()

    # Only select rows that are NaNs in rolling series
    blank_rolling_rows = rolling_rate.isna()
    expanding_rate = groups.expanding(1).mean()[blank_rolling_rows]

    return (
        pd.concat([rolling_rate, expanding_rate], join="inner")
        .dropna()
        .sort_index()
        .rename(f"rolling_{column}_rate")
    )


def calculate_rolling_rate(column: str) -> DataFrameCalculator:
    """Calculate the rolling mean of a column"""

    return partial(_rolling_rate, column)
