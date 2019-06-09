"""Module with wrapper class for Lasso model and its associated data class"""

from typing import List

from machine_learning.types import DataFrameTransformer, YearPair, DataReadersParam
from machine_learning.data_processors import (
    TeamDataStacker,
    FeatureBuilder,
    OppoFeatureBuilder,
)
from machine_learning.data_import import FootywireDataImporter
from machine_learning.data_processors.feature_functions import add_betting_pred_win
from machine_learning.data_processors.feature_calculation import (
    feature_calculator,
    calculate_rolling_rate,
)
from machine_learning.data_transformation import data_cleaning
from machine_learning.ml_data import BaseMLData
from machine_learning.data_config import INDEX_COLS
from machine_learning.utils import DataTransformerMixin


FEATURE_FUNCS: List[DataFrameTransformer] = [
    add_betting_pred_win,
    feature_calculator([(calculate_rolling_rate, [("betting_pred_win",)])]),
]

DATA_TRANSFORMERS: List[DataFrameTransformer] = [
    data_cleaning.clean_betting_data,
    TeamDataStacker().transform,
    FeatureBuilder(feature_funcs=FEATURE_FUNCS).transform,
    OppoFeatureBuilder(
        oppo_feature_cols=["betting_pred_win", "rolling_betting_pred_win_rate"]
    ).transform,
]


class BettingMLData(BaseMLData, DataTransformerMixin):
    """Load and clean betting data"""

    def __init__(
        self,
        data_readers: DataReadersParam = None,
        data_transformers: List[DataFrameTransformer] = DATA_TRANSFORMERS,
        train_years: YearPair = (None, 2015),
        test_years: YearPair = (2016, 2016),
        index_cols: List[str] = INDEX_COLS,
        fetch_data: bool = False,
    ) -> None:
        super().__init__(
            train_years=train_years, test_years=test_years, fetch_data=fetch_data
        )

        if data_readers is None:
            self.data_readers: DataReadersParam = {
                "betting": (FootywireDataImporter().get_betting_odds, {})
            }
        else:
            self.data_readers = data_readers

        self.index_cols = index_cols
        self._data_transformers = data_transformers
        self._data = None

    @property
    def data(self):
        if self._data is None:
            betting_data_reader, betting_data_kwargs = self.data_readers["betting"]
            betting_data = betting_data_reader(
                **{**betting_data_kwargs, **{"fetch_data": self.fetch_data}}
            )

            self._data = (
                self._compose_transformers(betting_data)  # pylint: disable=E1102
                .astype({"year": int})
                .fillna(0)
                .set_index(self.index_cols, drop=False)
                .rename_axis([None] * len(self.index_cols))
                .sort_index()
            )

        return self._data

    @property
    def data_transformers(self):
        return self._data_transformers
