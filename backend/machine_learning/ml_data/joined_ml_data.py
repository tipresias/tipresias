"""Module for machine learning data class that joins various data sources together"""

from typing import Type, List, Dict, Any, Tuple
from functools import reduce

import pandas as pd

from server.data_processors import FeatureBuilder
from server.data_processors.feature_calculation import (
    feature_calculator,
    calculate_division,
    calculate_multiplication,
)
from server.types import YearPair, DataFrameTransformer
from server.utils import DataTransformerMixin
from server.data_config import CATEGORY_COLS
from . import BaseMLData
from . import BettingMLData
from . import MatchMLData
from . import PlayerMLData


START_DATE = "1965-01-01"

DATA_TRANSFORMERS: List[DataFrameTransformer] = [
    FeatureBuilder(
        feature_funcs=[
            feature_calculator(
                [
                    (calculate_division, [("elo_rating", "win_odds")]),
                    (calculate_multiplication, [("win_odds", "ladder_position")]),
                ]
            )
        ]
    ).transform
]
DATA_READERS: List[Type[BaseMLData]] = [BettingMLData, PlayerMLData, MatchMLData]


class JoinedMLData(BaseMLData, DataTransformerMixin):
    """Load and clean data from all data sources"""

    def __init__(
        self,
        data_readers: List[Type[BaseMLData]] = DATA_READERS,
        data_reader_kwargs: List[Dict[str, Any]] = [{}, {}, {}],
        train_years: YearPair = (None, 2015),
        test_years: YearPair = (2016, 2016),
        category_cols: List[str] = CATEGORY_COLS,
        data_transformers: List[DataFrameTransformer] = DATA_TRANSFORMERS,
        fetch_data: bool = False,
    ) -> None:
        if len(data_readers) != len(data_reader_kwargs):
            raise ValueError(
                "There must be exactly one kwarg object per data reader object."
            )

        super().__init__(
            train_years=train_years, test_years=test_years, fetch_data=fetch_data
        )

        self._data_transformers = data_transformers

        data_frame = reduce(
            self.__concat_data_frames, zip(data_readers, data_reader_kwargs), None
        )
        numeric_data_frame = data_frame.select_dtypes(include="number").fillna(0)

        if category_cols is None:
            category_data_frame = data_frame.drop(numeric_data_frame.columns, axis=1)
        else:
            category_data_frame = data_frame[category_cols]

        sorted_data_frame = pd.concat([category_data_frame, numeric_data_frame], axis=1)

        self._data = (
            self._compose_transformers(sorted_data_frame)  # pylint: disable=E1102
            .dropna()
            .sort_index()
        )

        # For some reason the 'date' column in MatchMLData gets converted from 'datetime64'
        # to 'object' as part of the concatenation process.
        if "date" in self._data.columns:
            self._data.loc[:, "date"] = self._data["date"].pipe(pd.to_datetime)

    @property
    def data(self) -> pd.DataFrame:
        return self._data

    @property
    def data_transformers(self):
        return self._data_transformers

    def __concat_data_frames(
        self,
        concated_data_frame: pd.DataFrame,
        data: Tuple[Type[BaseMLData], Dict[str, Any]],
    ) -> pd.DataFrame:
        data_reader, data_kwargs = data
        data_reader_kwargs = {**data_kwargs, **{"fetch_data": self.fetch_data}}
        data_frame = data_reader(**data_reader_kwargs).data

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
