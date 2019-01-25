"""Module with wrapper class for XGBoost model and its associated data class"""

from typing import List, Optional, Sequence, Callable
import pandas as pd
import numpy as np
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.pipeline import make_pipeline, Pipeline
from xgboost import XGBRegressor

from server.types import DataFrameTransformer, YearPair
from server.data_processors import TeamDataStacker, FeatureBuilder, OppoFeatureBuilder
from server.data_processors.feature_functions import (
    add_last_week_result,
    add_last_week_score,
    add_cum_percent,
    add_cum_win_points,
    add_rolling_last_week_win_rate,
    add_ladder_position,
    add_win_streak,
    add_out_of_state,
    add_travel_distance,
    add_last_week_goals,
    add_last_week_behinds,
)
from server.data_readers import FitzroyDataReader
from server.ml_models.ml_model import MLModel, MLModelData, DataTransformerMixin
from server.ml_models.data_config import TEAM_NAMES, ROUND_TYPES

COL_TRANSLATIONS = {
    "home_points": "home_score",
    "away_points": "away_score",
    "margin": "home_margin",
    "season": "year",
}
INDEX_COLS = ["team", "year", "round_number"]
REQUIRED_COLS: List[str] = ["year", "score", "oppo_score"]
FEATURE_FUNCS: Sequence[DataFrameTransformer] = [
    add_out_of_state,
    add_travel_distance,
    add_last_week_goals,
    add_last_week_behinds,
    add_last_week_result,
    add_last_week_score,
    add_cum_win_points,
    add_rolling_last_week_win_rate,
    add_win_streak,
]
DATA_TRANSFORMERS: List[DataFrameTransformer] = [
    TeamDataStacker(index_cols=INDEX_COLS).transform,
    FeatureBuilder(feature_funcs=FEATURE_FUNCS).transform,
    OppoFeatureBuilder(
        match_cols=[
            "team",
            "year",
            "round_number",
            "score",
            "oppo_score",
            "out_of_state",
            "at_home",
            "oppo_team",
            "venue",
            "round_type",
        ]
    ).transform,
    # Features dependent on oppo columns
    FeatureBuilder(feature_funcs=[add_cum_percent, add_ladder_position]).transform,
    OppoFeatureBuilder(oppo_feature_cols=["cum_percent", "ladder_position"]).transform,
]
DATA_READERS: List[Callable] = [FitzroyDataReader().match_results]
MODEL_ESTIMATORS = ()
PIPELINE = make_pipeline(
    ColumnTransformer(
        [
            (
                "onehotencoder",
                OneHotEncoder(
                    categories=[TEAM_NAMES, TEAM_NAMES, ROUND_TYPES], sparse=False
                ),
                ["team", "oppo_team", "round_type"],
            )
        ],
        remainder="passthrough",
    ),
    StandardScaler(),
    XGBRegressor(),
)

np.random.seed(42)


class MatchModel(MLModel):
    """Create pipeline for fitting/predicting with model trained on match data"""

    def __init__(
        self, pipeline: Pipeline = PIPELINE, name: Optional[str] = None
    ) -> None:
        super().__init__(pipeline=pipeline, name=name)


class MatchModelData(MLModelData, DataTransformerMixin):
    """Load and clean match data"""

    def __init__(
        self,
        data_readers: List[Callable] = DATA_READERS,
        data_transformers: List[DataFrameTransformer] = DATA_TRANSFORMERS,
        train_years: YearPair = (None, 2015),
        test_years: YearPair = (2016, 2016),
    ) -> None:
        super().__init__(train_years=train_years, test_years=test_years)

        self._data_transformers = data_transformers

        data_frame = (
            data_readers[0]()
            .rename(columns=COL_TRANSLATIONS)
            .astype({"year": int})
            .drop(["round", "game", "date"], axis=1)
        )

        # There was some sort of round-robin finals round in 1897 and figuring out
        # a way to clean it up that makes sense is more trouble than just dropping a few rows
        data_frame = data_frame[
            (data_frame["year"] != 1897) | (data_frame["round_number"] != 15)
        ]

        self._data = (
            self._compose_transformers(data_frame)  # pylint: disable=E1102
            .drop("venue", axis=1)
            .fillna(0)
            .sort_index()
        )

    @property
    def data(self) -> pd.DataFrame:
        return self._data

    @property
    def data_transformers(self):
        return self._data_transformers
