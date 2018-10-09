"""Script for generating the pickle file for the LassoBetting estimator"""

import os
import sys

PROJECT_PATH: str = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '../../')
)

if PROJECT_PATH not in sys.path:
    sys.path.append(PROJECT_PATH)

from server.ml_models import MatchXGB
from server.ml_models.match_xgb import MatchXGBData


def main():
    data = MatchXGBData()
    estimator = MatchXGB()
    estimator.fit(*data.train_data())
    estimator.save()


if __name__ == '__main__':
    main()
