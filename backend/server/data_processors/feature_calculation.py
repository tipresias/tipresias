from typing import Tuple, List, Callable, Sequence
from functools import partial
import itertools
import pandas as pd

from server.types import DataFrameTransformer
from server.ml_models.data_config import AVG_SEASON_LENGTH

DataFrameCalculator = Callable[[pd.DataFrame], pd.Series]
Calculator = Callable[[Sequence[str]], DataFrameCalculator]
CalculatorPair = Tuple[Calculator, List[Sequence[str]]]

TEAM_LEVEL = 0


def _calculate_feature_col(
    data_calculator: Calculator, column_sets: List[Sequence[str]]
) -> List[DataFrameCalculator]:
    if len(column_sets) != len(set(column_sets)):
        raise ValueError(
            "Some column sets are duplicated, which will result in duplicate data frame "
            "columns. Make sure each column is calculated once."
        )

    return [data_calculator(column_set) for column_set in column_sets]


def _calculate_features(calculators: List[CalculatorPair], data_frame: pd.DataFrame):
    calculator_func_lists = [
        _calculate_feature_col(calculator, column_sets)
        for calculator, column_sets in calculators
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


def calculate_rolling_rate(column: Sequence[str]) -> DataFrameCalculator:
    """Calculate the rolling mean of a column"""

    if len(column) != 1:
        raise ValueError(
            "Can only calculate one rolling average at a time, but received "
            f"{column}"
        )
    return partial(_rolling_rate, column[0])


def _division(column_pair: Sequence[str], data_frame: pd.DataFrame) -> pd.Series:
    divisor, dividend = column_pair

    if divisor not in data_frame.columns or dividend not in data_frame.columns:
        raise ValueError(
            f"To calculate division of '{divisor}' by '{dividend}', both "
            "must be in data frame, but the columns given were "
            f"{data_frame.columns}"
        )

    return (data_frame[divisor] / data_frame[dividend]).rename(
        f"{divisor}_divided_by_{dividend}"
    )


def calculate_division(column_pair: Sequence[str]) -> DataFrameCalculator:
    """Calculates the first column's values divided by the second's"""

    if len(column_pair) != 2:
        raise ValueError(
            "Can only calculate one column divided by another, but received "
            f"{column_pair}"
        )

    return partial(_division, column_pair)


def _multiplication(column_pair: Sequence[str], data_frame: pd.DataFrame) -> pd.Series:
    first_col, second_col = column_pair
    if first_col not in data_frame.columns or second_col not in data_frame.columns:
        raise ValueError(
            f"To calculate multiplication of '{first_col}' by '{second_col}', "
            "both must be in data frame, but the columns given were "
            f"{data_frame.columns}"
        )

    return (data_frame[first_col] * data_frame[second_col]).rename(
        f"{first_col}_multiplied_by_{second_col}"
    )


def calculate_multiplication(column_pair: Sequence[str]) -> DataFrameCalculator:
    """Multiplies the values of the two columns"""

    if len(column_pair) != 2:
        raise ValueError(
            "Can only calculate one column multiplied by another, but received "
            f"{column_pair}"
        )

    return partial(_multiplication, column_pair)
