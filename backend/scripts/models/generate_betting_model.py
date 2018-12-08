"""Script for generating the pickle file for the LassoBetting estimator"""

from server.ml_models import BettingLasso
from server.ml_models.betting_lasso import BettingLassoData


def main():
    data = BettingLassoData()
    estimator = BettingLasso()
    estimator.fit(*data.train_data())
    estimator.save()


if __name__ == "__main__":
    main()
