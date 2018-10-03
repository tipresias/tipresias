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
DATA_TRANSFORMERS = [
    DataConcatenator().transform,
    DataCleaner().transform,
    TeamDataStacker().transform,
    FeatureBuilder().transform
]


# TODO: This will need a refactor, but I'll wait to see what other ML model classes
# look like before making decisions about data & dependencies
class BettingLasso():
    def __init__(self):
        self._pipeline = make_pipeline(StandardScaler(), Lasso())

    def fit(self, X, y):
        self._pipeline.fit(X, y)

    def predict(self, X):
        y_pred = self._pipeline.predict(X)

        return pd.DataFrame({'predicted_margin': y_pred}, index=X.index)

    def save(self, filepath=f'{PROJECT_PATH}/server/ml_models/betting_lasso_model.pkl'):
        joblib.dump(self._pipeline, filepath)

    def load(self, filepath=f'{PROJECT_PATH}/server/ml_models/betting_lasso_model.pkl'):
        self._pipeline = joblib.load(filepath)


class BettingLassoData():
    def __init__(self,
                 data_transformers=DATA_TRANSFORMERS,
                 training_years=(0, 2015),
                 test_years=(2016, 2016)):
        self.training_years = training_years
        self.test_years = test_years

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

    def training_data(self):
        data_train = self._data[
            (self._data['year'] >= self.training_years[0]) &
            (self._data['year'] <= self.training_years[1])
        ]
        X_train = self.__X(data_train, train=True)
        y_train = self.__y(data_train)

        return X_train, y_train

    def test_data(self):
        data_test = self._data[
            (self._data['year'] >= self.test_years[0]) &
            (self._data['year'] <= self.test_years[1])
        ]
        X_test = self.__X(data_test)
        y_test = self.__y(data_test)

        return X_test, y_test

    @staticmethod
    def __compose_two(composed_func, func_element):
        return lambda x: composed_func(func_element(x))

    @staticmethod
    def __X(data_frame, train=False):
        X_data = data_frame.drop(['score', 'oppo_score'], axis=1)

        if train:
            return pd.get_dummies(X_data)

        return X_data

    @staticmethod
    def __y(data_frame):
        return data_frame['score'] - data_frame['oppo_score']
