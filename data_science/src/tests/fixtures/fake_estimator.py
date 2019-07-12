from sklearn.linear_model import Lasso
from sklearn.pipeline import make_pipeline
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder

from machine_learning.ml_estimators import BaseMLEstimator
from machine_learning.ml_data import BettingMLData
from machine_learning.data_config import TEAM_NAMES

CATEGORY_COLS = ["team", "oppo_team"]
PIPELINE = make_pipeline(
    ColumnTransformer(
        [
            (
                "onehotencoder",
                OneHotEncoder(
                    categories=[TEAM_NAMES, TEAM_NAMES],
                    sparse=False,
                    handle_unknown="ignore",
                ),
                CATEGORY_COLS,
            )
        ],
        remainder="passthrough",
    ),
    Lasso(),
)


class FakeEstimator(BaseMLEstimator):
    """Create test MLModel for use in integration tests"""

    def __init__(self, pipeline=PIPELINE, name="fake_estimator"):
        super().__init__(pipeline=pipeline, name=name)


def pickle_fake_estimator():
    estimator = FakeEstimator()
    data = BettingMLData()

    estimator.fit(*data.train_data())
    estimator.dump()
