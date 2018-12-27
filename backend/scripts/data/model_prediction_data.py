"""Script for generating prediction data (in the form of a CSV) for all available models."""

import os
import sys
from typing import Tuple
import pandas as pd
import numpy as np
from dask import compute, delayed

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../"))

if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

from project.settings.common import DATA_DIR
from server.ml_models import BettingModel
from server.ml_models.betting_model import BettingModelData
from server.ml_models import MatchModel
from server.ml_models.match_model import MatchModelData
from server.ml_models import PlayerModel
from server.ml_models.player_model import PlayerModelData
from server.ml_models import AllModel
from server.ml_models.all_model import AllModelData
from server.ml_models import AvgModel

from notebooks.src.data.data_builder import DataBuilder, BettingData, MatchData
from notebooks.src.data.data_transformer import DataTransformer

DATA_FILES: Tuple[str, str] = ("afl_betting.csv", "ft_match_list.csv")
ML_MODELS = [
    (BettingModel(name="betting_data"), BettingModelData),
    (MatchModel(name="match_data"), MatchModelData),
    (PlayerModel(name="player_data"), PlayerModelData),
    (AllModel(name="all_data"), AllModelData),
    (AvgModel(name="avg_predictions"), AllModelData),
]

np.random.seed(42)


def make_year_prediction(estimator, data, year):
    data.train_years = (0, year - 1)
    data.test_years = (year, year)

    estimator.fit(*data.train_data())
    y_pred = estimator.predict(data.test_data()[0])
    year_pred_df = pd.concat(list(data.test_data()), axis=1).assign(
        predicted_margin=y_pred
    )

    return year_pred_df


def make_predictions(ml_model, ml_data) -> pd.DataFrame:
    """Generate prediction data frame for estimator based on player data"""

    data = ml_data(train_years=(None, None), test_years=(None, None))
    estimator = ml_model

    values = [
        delayed(make_year_prediction)(estimator, data, year)
        for year in range(2011, 2017)
    ]
    predictions = compute(*values, scheduler="processes")

    pred_df = pd.concat(predictions).sort_index()
    home_df = pred_df[pred_df["at_home"] == 1]

    return (
        home_df.loc[:, ["year", "round_number", "team", "oppo_team"]]
        .rename(columns={"team": "home_team", "oppo_team": "away_team"})
        .assign(
            model=ml_model.name,
            predicted_home_margin=(home_df["predicted_margin"].round()),
            home_margin=home_df["margin"],
            predicted_home_win=(home_df["predicted_margin"] > 0).astype(int),
            home_win=(home_df["margin"] > 0).astype(int),
            draw=(home_df["margin"] == 0).astype(int),
        )
        .assign(
            tip_point=lambda x: (
                (x["predicted_home_win"] == x["home_win"]) | (x["draw"])
            ).astype(int)
        )
        .reset_index(drop=True)
    )


def oddsmakers_predictions() -> pd.DataFrame:
    """Generate prediction data frame based on raw betting odds"""

    csv_paths = [os.path.join(DATA_DIR, data_file) for data_file in DATA_FILES]
    data_classes = (BettingData, MatchData)

    raw_df = DataBuilder(data_classes, csv_paths).concat()
    transformer = DataTransformer(raw_df)

    clean_df = transformer.clean()

    # Get predictions after 2010, because betting data starts in 2010, so associated
    # models can only start predicting for 2011 season
    return (
        clean_df[clean_df["year"] > 2010]
        .loc[:, ["year", "round_number", "home_team", "away_team"]]
        .assign(
            model="oddsmakers",
            # Rounding predicted margin, because you can't actually
            # predict fractions of a point
            predicted_home_margin=clean_df["home_line_odds"].round() * -1,
            home_margin=clean_df["home_score"] - clean_df["away_score"],
            predicted_home_win=(
                (
                    (clean_df["home_win_odds"] < clean_df["away_win_odds"])
                    | (clean_df["home_line_odds"] < clean_df["away_line_odds"])
                    |
                    # If odds are all equal, predict home team
                    (
                        (clean_df["home_win_odds"] == clean_df["away_win_odds"])
                        & (clean_df["home_line_odds"] == clean_df["away_line_odds"])
                    )
                ).astype(int)
            ),
            home_win=(clean_df["home_score"] > clean_df["away_score"]).astype(int),
            draw=(clean_df["home_score"] == clean_df["away_score"]).astype(int),
        )
        .assign(
            tip_point=lambda x: (
                (x["predicted_home_win"] == x["home_win"]) | (x["draw"])
            ).astype(int)
        )
    )


def main():
    """The main function. Where the magic happens"""
    model_predictions = [make_predictions(*ml_model) for ml_model in ML_MODELS]

    pd.concat([oddsmakers_predictions(), *model_predictions]).to_csv(
        f"{DATA_DIR}/model_predictions.csv", index=False
    )


main()
