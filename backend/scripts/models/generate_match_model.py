"""Script for generating the pickle file for the LassoBetting estimator"""

from server.ml_models import MatchModel
from server.ml_models.match_model import MatchModelData


def main():
    data = MatchModelData()
    estimator = MatchModel()
    estimator.fit(*data.train_data())
    estimator.save()


if __name__ == "__main__":
    main()
