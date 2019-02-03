"""Class for model trained on all AFL data and its associated data class"""

import warnings
from typing import List, Optional, Type, Dict, Any, Tuple
from datetime import datetime
from functools import reduce
import pandas as pd
import numpy as np
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.pipeline import make_pipeline, Pipeline
from sklearn.exceptions import DataConversionWarning
from xgboost import XGBRegressor

from server.ml_models.betting_model import BettingModelData
from server.ml_models.match_model import MatchModelData, CATEGORY_COLS
from server.ml_models.player_model import PlayerModelData
from server.ml_models.ml_model import MLModel, MLModelData
from server.types import YearPair
from server.ml_models.data_config import TEAM_NAMES, ROUND_TYPES, VENUES, SEED


START_DATE = "1965-01-01"
DATA_READERS: List[Type[MLModelData]] = [
    BettingModelData,
    PlayerModelData,
    MatchModelData,
]
PIPELINE = make_pipeline(
    ColumnTransformer(
        [
            (
                "onehotencoder",
                OneHotEncoder(
                    categories=[TEAM_NAMES, TEAM_NAMES, ROUND_TYPES, VENUES],
                    sparse=False,
                ),
                CATEGORY_COLS,
            )
        ],
        remainder=StandardScaler(),
    ),
    XGBRegressor(),
)

# Using ColumnTransformer to run OneHotEncoder & StandardScaler causes this warning
# when using BaggingRegressor, because BR converts the DataFrame to a numpy array,
# which results in all rows having type 'object', because they include strings and floats
warnings.simplefilter("ignore", DataConversionWarning)

np.random.seed(SEED)


class AllModel(MLModel):
    """Create pipeline for fitting/predicting with model trained on all AFL data"""

    def __init__(
        self, pipeline: Pipeline = PIPELINE, name: Optional[str] = None
    ) -> None:
        super().__init__(pipeline=pipeline, name=name)


class AllModelData(MLModelData):
    """Load and clean data from all data sources"""

    def __init__(
        self,
        data_readers: List[Type[MLModelData]] = DATA_READERS,
        data_reader_kwargs: List[Dict[str, Any]] = [{}, {}, {}],
        train_years: YearPair = (None, 2015),
        test_years: YearPair = (2016, 2016),
        start_date=None,
        end_date="2016-12-31",
        category_cols=CATEGORY_COLS,
    ) -> None:
        if len(data_readers) != len(data_reader_kwargs):
            raise ValueError(
                "There must be exactly one kwarg object per data reader object."
            )

        super().__init__(train_years=train_years, test_years=test_years)

        data_frame = reduce(
            self.__concat_data_frames, zip(data_readers, data_reader_kwargs), None
        )
        numeric_data_frame = data_frame.select_dtypes(
            include=["number", "datetime"]
        ).fillna(0)

        if category_cols is None:
            category_data_frame = data_frame.drop(numeric_data_frame.columns, axis=1)
        else:
            category_data_frame = data_frame[category_cols]

        start_year = datetime.strptime(start_date, "%Y-%m-%d").year if start_date else 0
        end_year = datetime.strptime(end_date, "%Y-%m-%d").year if end_date else np.Inf

        self._data = (
            pd.concat([category_data_frame, numeric_data_frame], axis=1)
            .loc[(data_frame["year"] >= start_year) & (data_frame["year"] <= end_year),]
            .dropna()
            .sort_index()
        )

    @property
    def data(self) -> pd.DataFrame:
        return self._data

    @staticmethod
    def __concat_data_frames(
        concated_data_frame: pd.DataFrame,
        data: Tuple[Type[MLModelData], Dict[str, Any]],
    ) -> pd.DataFrame:
        data_reader, data_kwargs = data
        data_frame = data_reader(**data_kwargs).data

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
