import os
from functools import reduce
import pandas as pd
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import Lasso
from sklearn.externals import joblib

from server.data_processors import (
    DataConcatenator,
    DataCleaner,
    TeamDataStacker,
    FeatureBuilder,
    BettingDataReader,
    MatchDataReader
)

PROJECT_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '../../')
)

DATA_FILES = ('afl_betting.csv', 'ft_match_list.csv')
REQUIRED_COLS = ['year', 'score', 'oppo_score']


# TODO: This will need a refactor, but I'll wait to see what other ML model classes
# look like before making decisions about data & dependencies
class BettingLasso():
    def __init__(self):
        data_transformers = [
            DataConcatenator().transform,
            DataCleaner(max_year=2016).transform,
            TeamDataStacker().transform,
            FeatureBuilder().transform
        ]

        # Need to reverse the transformation steps, because composition makes the output
        # of each new function the argument for the previous
        compose_all = reduce(
            self.__compose_two, reversed(data_transformers), lambda x: x
        )

        self._data = pd.get_dummies(
            compose_all([BettingDataReader().transform(),
                         MatchDataReader().transform()])
            .dropna()
        )

        if any([req_col not in self._data.columns for req_col in REQUIRED_COLS]):
            raise ValueError('To fit model & predict, all required columns '
                             f'({REQUIRED_COLS}) must be in the data frame, '
                             f'but the columns given were {self._data.columns}')

        self._pipeline = make_pipeline(StandardScaler(), Lasso())

    def fit(self, min_year=1, max_year=2015):
        training_data = self._data[
            (self._data['year'] >= min_year) & (self._data['year'] <= max_year)
        ]
        X_train = pd.get_dummies(
            training_data.drop(['score', 'oppo_score'], axis=1)
        )
        y_train = training_data['score'] - training_data['oppo_score']

        self._pipeline.fit(X_train, y_train)

    def predict(self, min_year=2016, max_year=2016):
        test_data = self._data[
            (self._data['year'] >= min_year) & (self._data['year'] <= max_year)
        ]
        X_test = test_data.drop(['score', 'oppo_score'], axis=1)
        y_pred = self._pipeline.predict(X_test)

        return pd.DataFrame({'predicted_margin': y_pred}, index=test_data.index)

    def save(self):
        joblib.dump(self._pipeline,
                    f'{PROJECT_PATH}/server/ml_models/betting_lasso_model.pkl')

    def load(self):
        self._pipeline = joblib.load(
            f'{PROJECT_PATH}/server/ml_models/betting_lasso_model.pkl'
        )

    @staticmethod
    def __compose_two(composed_func, func_element):
        return lambda x: composed_func(func_element(x))
