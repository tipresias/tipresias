"""Script for generating the pickle file for the ModelBetting estimator"""

from server.ml_models import BettingModel
from server.ml_models.betting_model import BettingModelData


def main():
    data = BettingModelData()
    estimator = BettingModel()
    estimator.fit(*data.train_data())
    estimator.save()


if __name__ == "__main__":
    main()
