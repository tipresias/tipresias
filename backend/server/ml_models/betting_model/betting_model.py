"""Module with wrapper class for Lasso model and its associated data class"""

from typing import List, Optional, Sequence, Any
import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import Lasso
from sklearn.base import BaseEstimator

from server.types import DataFrameTransformer, YearPair
from server.data_processors import TeamDataStacker, FeatureBuilder, OppoFeatureBuilder
from server.data_readers import FootyWireDataReader
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

BETTING_TEAM_TRANSLATIONS = {
    "Tigers": "Richmond",
    "Blues": "Carlton",
    "Demons": "Melbourne",
    "Giants": "GWS",
    "Suns": "Gold Coast",
    "Bombers": "Essendon",
    "Swans": "Sydney",
    "Magpies": "Collingwood",
    "Kangaroos": "North Melbourne",
    "Crows": "Adelaide",
    "Bulldogs": "Western Bulldogs",
    "Dockers": "Fremantle",
    "Power": "Port Adelaide",
    "Saints": "St Kilda",
    "Eagles": "West Coast",
    "Lions": "Brisbane",
    "Cats": "Geelong",
    "Hawks": "Hawthorn",
    "Adelaide Crows": "Adelaide",
    "Brisbane Lions": "Brisbane",
    "Gold Coast Suns": "Gold Coast",
    "GWS Giants": "GWS",
    "Geelong Cats": "Geelong",
    "West Coast Eagles": "West Coast",
    "Sydney Swans": "Sydney",
}
VENUE_TRANSLATIONS = {
    "AAMI": "AAMI Stadium",
    "ANZ": "ANZ Stadium",
    "Adelaide": "Adelaide Oval",
    "Aurora": "UTAS Stadium",
    "Aurora Stadium": "UTAS Stadium",
    "Blacktown": "Blacktown International",
    "Blundstone": "Blundstone Arena",
    "Cazaly's": "Cazaly's Stadium",
    "Domain": "Domain Stadium",
    "Etihad": "Etihad Stadium",
    "GMHBA": "GMHBA Stadium",
    "Gabba": "Gabba",
    "Jiangwan": "Jiangwan Stadium",
    "MCG": "MCG",
    "Mars": "Mars Stadium",
    "Metricon": "Metricon Stadium",
    "Perth": "Optus Stadium",
    "SCG": "SCG",
    "Spotless": "Spotless Stadium",
    "StarTrack": "Manuka Oval",
    "TIO": "TIO Stadium",
    "UTAS": "UTAS Stadium",
    "Westpac": "Westpac Stadium",
    "TIO Traegar Park": "TIO Stadium",
}

FEATURE_FUNCS: Sequence[DataFrameTransformer] = (
    add_last_week_result,
    add_last_week_score,
    add_cum_win_points,
    add_rolling_pred_win_rate,
    add_rolling_last_week_win_rate,
    add_win_streak,
)
REQUIRED_COLS: List[str] = ["year", "score", "oppo_score"]
DATA_TRANSFORMERS: List[DataFrameTransformer] = [
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
DATA_READERS = [
    FootyWireDataReader().get_betting_odds(),
    FootyWireDataReader().get_fixture(),
]
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
    ) -> None:
        super().__init__(estimators=estimators, name=name)


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

        data_frame = (
            self.__concat_data_input(data_readers)
            .rename(columns={"season": "year", "round": "round_number"})
            .drop(
                [
                    "crowd",
                    "home_win_paid",
                    "home_line_paid",
                    "away_win_paid",
                    "away_line_paid",
                ],
                axis=1,
            )
        )

        self._data = (
            self._compose_transformers(data_frame)  # pylint: disable=E1102
            .astype({"year": int})
            .fillna(0)
            .sort_index()
        )

    @property
    def data(self):
        return self._data

    @property
    def data_transformers(self):
        return self._data_transformers

    @staticmethod
    def __concat_data_input(data_frames: List[pd.DataFrame]) -> pd.DataFrame:
        betting_data = (
            data_frames[0]
            .drop(
                [
                    "date",
                    "venue",
                    "round_label",
                    "home_score",
                    "home_margin",
                    "away_score",
                    "away_margin",
                ],
                axis=1,
            )
            .assign(
                home_team=lambda df: df["home_team"].map(BETTING_TEAM_TRANSLATIONS),
                away_team=lambda df: df["away_team"].map(BETTING_TEAM_TRANSLATIONS),
            )
        )
        match_data = data_frames[1].drop(["date", "venue", "round_label"], axis=1)

        return betting_data.merge(
            match_data, on=["home_team", "away_team", "round", "season"]
        )
