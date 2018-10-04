import os
from functools import reduce
import pandas as pd
import numpy as np
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
    os.path.join(os.path.dirname(__file__), '../../../')
)

REQUIRED_COLS = ['year', 'score', 'oppo_score']
DATA_TRANSFORMERS = [
    DataConcatenator().transform,
    DataCleaner().transform,
    TeamDataStacker().transform,
    FeatureBuilder().transform
]

np.random.seed(42)


# TODO: This will need a refactor, but I'll wait to see what other ML model classes
# look like before making decisions about data & dependencies
class BettingLasso():
    def __init__(self):
        self._pipeline = make_pipeline(StandardScaler(), Lasso())
        self.name = self.__name()

    def fit(self, X, y):
        self._pipeline.fit(X, y)

    def predict(self, X):
        y_pred = self._pipeline.predict(X)

        return pd.Series(y_pred, name='predicted_margin', index=X.index)

    def save(self,
             filepath=f'{PROJECT_PATH}/server/ml_models/betting_lasso/betting_lasso_model.pkl'):
        joblib.dump(self._pipeline, filepath)

    def load(self,
             filepath=f'{PROJECT_PATH}/server/ml_models/betting_lasso/betting_lasso_model.pkl'):
        self._pipeline = joblib.load(filepath)

    def __name(self):
        return self.__last_estimator()[0]

    def __last_estimator(self):
        return self._pipeline.steps[-1]


class BettingLassoData():
    def __init__(self,
                 data_transformers=DATA_TRANSFORMERS,
                 train_years=(None, 2015),
                 test_years=(2016, 2016)):
        self._train_years = train_years
        self._test_years = test_years

        # Need to reverse the transformation steps, because composition makes the output
        # of each new function the argument for the previous
        compose_all = reduce(
            self.__compose_two, reversed(data_transformers), lambda x: x
        )

        self.data = (compose_all([BettingDataReader().transform(),
                                  MatchDataReader().transform()])
                     .dropna()
                     )

    def train_data(self):
        data_train = self.data[
            (self.data['year'] >= self.__train_min()) &
            (self.data['year'] <= self.__train_max())
        ]

        X_train = self.__X(data_train)
        y_train = self.__y(data_train)

        return X_train, y_train

    def test_data(self):
        data_test = self.data[
            (self.data['year'] >= self.__test_min()) &
            (self.data['year'] <= self.__test_max())
        ]
        X_test = self.__X(data_test)
        y_test = self.__y(data_test)

        return X_test, y_test

    @property
    def train_years(self):
        return self._train_years

    @train_years.setter
    def train_years(self, years):
        self._train_years = years

    @property
    def test_years(self):
        return self._test_years

    @test_years.setter
    def test_years(self, years):
        self._test_years = years

    def __train_min(self):
        return self._train_years[0] or np.NINF

    def __train_max(self):
        return self._train_years[1] or np.Inf

    def __test_min(self):
        return self._test_years[0] or np.NINF

    def __test_max(self):
        return self._test_years[1] or np.Inf

    def __X(self, data_frame):
        data_dummies = pd.get_dummies(self.data.select_dtypes('O'))
        X_data = pd.get_dummies(
            data_frame.drop(['score', 'oppo_score'], axis=1)
        )

        # Have to get missing dummy columns, because train & test years can have different
        # teams/venues, resulting in data mismatch when trying to predict with a model
        missing_cols = np.setdiff1d(data_dummies.columns, X_data.columns)
        missing_df = pd.DataFrame(
            {missing_col: 0 for missing_col in missing_cols}, index=X_data.index
        )

        return pd.concat([X_data, missing_df], axis=1)

    @staticmethod
    def __compose_two(composed_func, func_element):
        return lambda x: composed_func(func_element(x))

    @staticmethod
    def __y(data_frame):
        return data_frame['score'] - data_frame['oppo_score']
