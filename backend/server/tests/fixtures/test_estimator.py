from sklearn.linear_model import Lasso
from sklearn.pipeline import make_pipeline
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder

from server.ml_models import BaseMLModel
from server.ml_data import BettingMLData
from server.data_config import TEAM_NAMES

CATEGORY_COLS = ["team", "oppo_team"]
PIPELINE = make_pipeline(
    ColumnTransformer(
        [
            (
                "onehotencoder",
                OneHotEncoder(categories=[TEAM_NAMES, TEAM_NAMES], sparse=False),
                CATEGORY_COLS,
            )
        ],
        remainder="passthrough",
    ),
    Lasso(),
)


class TestEstimator(BaseMLModel):
    """Create test MLModel for use in integration tests"""

    def __init__(self, pipeline=PIPELINE, name="test_estimator"):
        super().__init__(pipeline=pipeline, name=name)


def pickle_test_estimator():
    estimator = TestEstimator()
    data = BettingMLData()

    estimator.fit(*data.train_data())
    estimator.dump()
