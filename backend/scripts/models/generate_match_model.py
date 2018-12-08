"""Script for generating the pickle file for the LassoBetting estimator"""

import os
import sys

from server.ml_models import MatchXGB
from server.ml_models.match_xgb import MatchXGBData


def main():
    data = MatchXGBData()
    estimator = MatchXGB()
    estimator.fit(*data.train_data())
    estimator.save()


if __name__ == "__main__":
    main()
