"""Script for generating the pickle file for the PlayerXGB estimator"""

import os
import sys

from server.ml_models import PlayerXGB
from server.ml_models.player_xgb import PlayerXGBData


def main():
    data = PlayerXGBData()
    estimator = PlayerXGB()
    estimator.fit(*data.train_data())
    estimator.save()


if __name__ == "__main__":
    main()
