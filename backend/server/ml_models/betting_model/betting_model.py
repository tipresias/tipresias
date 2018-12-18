"""Module with wrapper class for Lasso model and its associated data class"""

from typing import List, Optional, Sequence, Any
from functools import reduce
import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import Lasso
from sklearn.base import BaseEstimator

from server.types import DataFrameTransformer, YearPair
from server.data_processors import (
    DataCleaner,
    TeamDataStacker,
    FeatureBuilder,
    BettingDataReader,
    MatchDataReader,
    OppoFeatureBuilder,
)
from server.data_processors.feature_functions import (
    add_last_week_result,
    add_last_week_score,
    add_cum_percent,
    add_cum_win_points,
    add_rolling_pred_win_rate,
    add_rolling_last_week_win_rate,
    add_ladder_position,
    add_win_streak,
)
from server.ml_models.ml_model import MLModel, MLModelData, DataTransformerMixin

FEATURE_FUNCS: Sequence[DataFrameTransformer] = (
    add_last_week_result,
    add_last_week_score,
    add_cum_win_points,
    add_rolling_pred_win_rate,
    add_rolling_last_week_win_rate,
    add_win_streak,
)
REQUIRED_COLS: List[str] = ["year", "score", "oppo_score"]
DATA_TRANSFORMERS = [
    DataCleaner().transform,
    TeamDataStacker().transform,
    FeatureBuilder(feature_funcs=FEATURE_FUNCS).transform,
    OppoFeatureBuilder(
        match_cols=[
            "year",
            "score",
            "oppo_score",
            "round_number",
            "team",
            "at_home",
            "line_odds",
            "oppo_line_odds",
            "win_odds",
            "oppo_win_odds",
            "oppo_team",
        ]
    ).transform,
    # Features dependent on oppo columns
    FeatureBuilder(feature_funcs=[add_cum_percent, add_ladder_position]).transform,
]
DATA_READERS = [BettingDataReader().transform(), MatchDataReader().transform()]
MODEL_ESTIMATORS = (StandardScaler(), Lasso())

np.random.seed(42)


class BettingModel(MLModel):
    """Create pipeline for for fitting/predicting with lasso model.

    Attributes:
        _pipeline (sklearn.pipeline.Pipeline): Scikit Learn pipeline
            with transformers & Lasso estimator.
        name (string): Name of final estimator in the pipeline ('Lasso').
    """

    def __init__(
        self,
        estimators: Sequence[BaseEstimator] = MODEL_ESTIMATORS,
        name: Optional[str] = None,
        module_name: str = "",
    ) -> None:
        super().__init__(estimators=estimators, name=name, module_name=module_name)


class BettingModelData(MLModelData, DataTransformerMixin):
    """Load and clean betting data"""

    def __init__(
        self,
        data_readers: List[Any] = DATA_READERS,
        data_transformers: List[DataFrameTransformer] = DATA_TRANSFORMERS,
        train_years: YearPair = (None, 2015),
        test_years: YearPair = (2016, 2016),
    ) -> None:
        super().__init__(train_years=train_years, test_years=test_years)

        self._data_transformers = data_transformers

        data_frame = self.__concat_data_input(data_readers)
        self._data = (
            self._compose_transformers(data_frame)  # pylint: disable=E1102
            .astype({"year": int})
            .dropna()
        )

    @property
    def data(self):
        return self._data

    @property
    def data_transformers(self):
        return self._data_transformers

    @staticmethod
    def __concat_data_input(data_frames: List[pd.DataFrame]) -> pd.DataFrame:
        shared_columns = reduce(
            np.intersect1d, (data_frame.columns for data_frame in data_frames)
        )

        if not any(shared_columns):
            raise ValueError(
                "The data frames do not have any columns in common "
                "and cannot be concatenated."
            )

        reindexed_data_frames = [
            data_frame.set_index(list(shared_columns)) for data_frame in data_frames
        ]

        return (
            pd.concat(reindexed_data_frames, axis=1)
            .dropna()
            .reset_index()
            .drop("date", axis=1)
        )
