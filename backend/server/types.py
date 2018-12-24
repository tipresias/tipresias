"""Module for custom static data types"""

# pylint: disable=C0103

from typing import Callable, Tuple, Optional, TypeVar
import pandas as pd
from sklearn.base import BaseEstimator, RegressorMixin

DataFrameTransformer = Callable[[pd.DataFrame], pd.DataFrame]
YearPair = Tuple[Optional[int], Optional[int]]

M = TypeVar("M", BaseEstimator, RegressorMixin)
