from typing import Callable
import pandas as pd

FeatureFunctionType = Callable[[pd.DataFrame], pd.DataFrame]
