"""Class for model trained on all AFL data and its associated data class"""

from typing import List, Sequence, Optional, Type
from datetime import datetime
from functools import reduce
import pandas as pd
import numpy as np
from sklearn.base import BaseEstimator
from sklearn.preprocessing import StandardScaler
from xgboost import XGBRegressor

from server.ml_models.betting_model import BettingModelData
from server.ml_models.match_model import MatchModelData
from server.ml_models.player_model import PlayerModelData
from server.ml_models.ml_model import MLModel, MLModelData
from server.types import YearPair


START_DATE = "1965-01-01"
DATA_READERS: List[Type[MLModelData]] = [
    BettingModelData,
    PlayerModelData,
    MatchModelData,
]
MODEL_ESTIMATORS = (StandardScaler(), XGBRegressor())

np.random.seed(42)


class AllModel(MLModel):
    """Create pipeline for fitting/predicting with model trained on all AFL data"""

    def __init__(
        self,
        estimators: Sequence[BaseEstimator] = MODEL_ESTIMATORS,
        name: Optional[str] = None,
    ) -> None:
        super().__init__(estimators=estimators, name=name)


class AllModelData(MLModelData):
    """Load and clean data from all data sources"""

    def __init__(
        self,
        data_readers: List[Type[MLModelData]] = DATA_READERS,
        train_years: YearPair = (None, 2015),
        test_years: YearPair = (2016, 2016),
        start_date=None,
        end_date="2016-12-31",
    ) -> None:
        super().__init__(train_years=train_years, test_years=test_years)

        data_frame = reduce(self.__concat_data_frames, data_readers, None)

        data_frame_dtypes = data_frame.dtypes
        numeric_cols_filter = (
            (data_frame_dtypes == float) | (data_frame_dtypes == int)
        ).values
        numeric_cols = data_frame.columns[numeric_cols_filter]
        fillna_dict = {col: 0 for col in numeric_cols}

        start_year = datetime.strptime(start_date, "%Y-%m-%d").year if start_date else 0
        end_year = datetime.strptime(end_date, "%Y-%m-%d").year if end_date else np.Inf

        self._data = (
            data_frame[
                (data_frame["year"] >= start_year) & (data_frame["year"] <= end_year)
            ]
            .fillna(fillna_dict)
            .dropna()
            .sort_index()
        )

    @property
    def data(self) -> pd.DataFrame:
        return self._data

    @staticmethod
    def __concat_data_frames(
        concated_data_frame: pd.DataFrame, data_reader: Type[MLModelData]
    ) -> pd.DataFrame:
        data_frame = data_reader().data

        if concated_data_frame is None:
            return data_frame

        agg_cols = set(concated_data_frame.columns)
        df_cols = set(data_frame.columns)
        drop_cols = agg_cols.intersection(df_cols)

        # Have to drop shared columns, and this seems a reasonable way of doing it
        # without hard-coding values.
        # TODO: Make this a little more robust by doing some fillna with shared columns,
        # because this currently relies on ordering data from smallest to largest
        # and knowing that larger datasets contain all shared data contained in
        # smaller data sets plus more.
        return pd.concat(
            [concated_data_frame.drop(list(drop_cols), axis=1), data_frame], axis=1
        )
