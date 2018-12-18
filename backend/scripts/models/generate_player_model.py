"""Script for generating the pickle file for the PlayerModel estimator"""

from server.ml_models import PlayerModel
from server.ml_models.player_model import PlayerModelData


def main():
    data = PlayerModelData()
    estimator = PlayerModel()
    estimator.fit(*data.train_data())
    estimator.save()


if __name__ == "__main__":
    main()
