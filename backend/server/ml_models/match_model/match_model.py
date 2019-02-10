"""Module with wrapper class for XGBoost model and its associated data class"""

from typing import List, Optional, Callable
import pandas as pd
import numpy as np
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.pipeline import make_pipeline, Pipeline
from xgboost import XGBRegressor

from server.types import DataFrameTransformer, YearPair
from server.data_processors import TeamDataStacker, FeatureBuilder, OppoFeatureBuilder
from server.data_processors.feature_functions import (
    add_result,
    add_margin,
    add_cum_percent,
    add_cum_win_points,
    add_ladder_position,
    add_win_streak,
    add_out_of_state,
    add_travel_distance,
    add_elo_rating,
    add_elo_pred_win,
    add_shifted_team_features,
)
from server.data_processors.feature_calculation import (
    feature_calculator,
    calculate_rolling_rate,
    calculate_division,
)
from server.data_readers import FitzroyDataReader
from server.ml_models.ml_model import MLModel, MLModelData, DataTransformerMixin
from server.ml_models.data_config import (
    TEAM_NAMES,
    ROUND_TYPES,
    INDEX_COLS,
    VENUES,
    SEED,
)

COL_TRANSLATIONS = {
    "home_points": "home_score",
    "away_points": "away_score",
    "margin": "home_margin",
    "season": "year",
}
CATEGORY_COLS = ["team", "oppo_team", "round_type", "venue"]
FEATURE_FUNCS: List[DataFrameTransformer] = [
    add_out_of_state,
    add_travel_distance,
    add_result,
    add_margin,
    add_shifted_team_features(
        shift_columns=["score", "oppo_score", "result", "margin", "goals", "behinds"]
    ),
    add_cum_win_points,
    add_win_streak,
    add_elo_rating,
    feature_calculator([(calculate_rolling_rate, [("result",)])]),
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
            "date",
        ]
    ).transform,
    # Features dependent on oppo columns
    FeatureBuilder(
        feature_funcs=[
            add_cum_percent,
            add_ladder_position,
            add_elo_pred_win,
            feature_calculator(
                [
                    (calculate_rolling_rate, [("elo_pred_win",)]),
                    (calculate_division, [("elo_rating", "ladder_position")]),
                ]
            ),
        ]
    ).transform,
    OppoFeatureBuilder(
        oppo_feature_cols=["cum_percent", "ladder_position", "elo_pred_win"]
    ).transform,
]
DATA_READERS: List[Callable] = [FitzroyDataReader().match_results]
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
        remainder="passthrough",
    ),
    StandardScaler(),
    XGBRegressor(),
)

np.random.seed(SEED)


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
        index_cols: List[str] = INDEX_COLS,
    ) -> None:
        super().__init__(train_years=train_years, test_years=test_years)

        self._data_transformers = data_transformers

        data_frame = (
            data_readers[0]()
            .rename(columns=COL_TRANSLATIONS)
            # fitzRoy returns integers that represent some sort of datetime, and the only
            # way to parse them is converting them to dates.
            # NOTE: If the matches parsed only go back to 1990 (give or take, I can't remember)
            # you can parse the date integers into datetime
            .assign(date=lambda df: pd.to_datetime(df["date"], unit="D"))
            .astype({"year": int})
            .drop(["round", "game"], axis=1)
        )

        # There were some weird round-robin rounds in the early days, and it's easier to
        # drop them rather than figure out how to split up the rounds.
        data_frame = data_frame[
            ((data_frame["year"] != 1897) | (data_frame["round_number"] != 15))
            & ((data_frame["year"] != 1924) | (data_frame["round_number"] != 19))
        ]

        self._data = (
            self._compose_transformers(data_frame)  # pylint: disable=E1102
            .fillna(0)
            .set_index(index_cols, drop=False)
            .rename_axis([None] * len(index_cols))
            .sort_index()
        )

    @property
    def data(self) -> pd.DataFrame:
        return self._data

    @property
    def data_transformers(self):
        return self._data_transformers
