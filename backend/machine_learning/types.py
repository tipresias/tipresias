"""Module for custom static data types"""

# pylint: disable=C0103

from typing import Callable, Tuple, Optional, TypeVar, Dict, Any
import pandas as pd
from sklearn.base import BaseEstimator, RegressorMixin, TransformerMixin

DataFrameTransformer = Callable[[pd.DataFrame], pd.DataFrame]
YearPair = Tuple[Optional[int], Optional[int]]
DataReadersParam = Dict[str, Tuple[Callable, Dict[str, Any]]]

R = TypeVar("R", BaseEstimator, RegressorMixin)
T = TypeVar("T", BaseEstimator, TransformerMixin)
