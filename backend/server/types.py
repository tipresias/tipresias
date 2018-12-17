"""Module for custom static data types"""

# pylint: disable=C0103

from typing import Callable, Tuple, Optional
import pandas as pd

DataFrameTransformer = Callable[[pd.DataFrame], pd.DataFrame]
YearPair = Tuple[Optional[int], Optional[int]]
