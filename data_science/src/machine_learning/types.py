"""Module for custom static data types"""

# pylint: disable=C0103

from typing import Callable, Tuple, Optional, TypeVar, Dict, Any, List, Sequence, Union
import pandas as pd
from sklearn.base import BaseEstimator, RegressorMixin, TransformerMixin

DataFrameTransformer = Callable[[Union[pd.DataFrame, List[pd.DataFrame]]], pd.DataFrame]
YearPair = Tuple[Optional[int], Optional[int]]
DataReadersParam = Dict[str, Tuple[Callable, Dict[str, Any]]]

DataFrameCalculator = Callable[[pd.DataFrame], pd.Series]
Calculator = Callable[[Sequence[str]], DataFrameCalculator]
CalculatorPair = Tuple[Calculator, List[Sequence[str]]]

R = TypeVar("R", BaseEstimator, RegressorMixin)
T = TypeVar("T", BaseEstimator, TransformerMixin)
