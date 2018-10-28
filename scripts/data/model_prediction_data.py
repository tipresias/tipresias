"""Script for generating prediction data (in the form of a CSV) for all available models."""

from typing import Tuple
import os
import sys
import pandas as pd

PROJECT_PATH: str = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '../../')
)
if PROJECT_PATH not in sys.path:
    sys.path.append(PROJECT_PATH)

from server.ml_models import BettingLasso
from server.ml_models.betting_lasso import BettingLassoData
from server.ml_models import MatchXGB
from server.ml_models.match_xgb import MatchXGBData
from server.ml_models import PlayerRidge
from server.ml_models.player_ridge import PlayerRidgeData

from notebooks.src.data.data_builder import DataBuilder, BettingData, MatchData
from notebooks.src.data.data_transformer import DataTransformer

DATA_FILES: Tuple[str, str] = ('afl_betting.csv', 'ft_match_list.csv')


def tipresias_player_predictions() -> pd.DataFrame:
    """Generate prediction data frame for estimator based on player data

    Returns:
        pandas.DataFrame
    """

    data = PlayerRidgeData(train_years=(None, None), test_years=(None, None))
    estimator = PlayerRidge()

    predictions = []

    for test_year in range(2011, 2017):
        data.train_years = (0, test_year - 1)
        data.test_years = (test_year, test_year)

        estimator.fit(*data.train_data())
        y_pred = estimator.predict(data.test_data()[0])

        predictions.append(y_pred)

    pred_col = pd.concat(predictions)

    pred_df = pd.concat([data.data, pred_col], join='inner', axis=1)
    home_df = pred_df[pred_df['at_home'] == 1]

    return (home_df.loc[:, ['year', 'round_number', 'team', 'oppo_team']]
            .rename(columns={'team': 'home_team', 'oppo_team': 'away_team'})
            .assign(model='tipresias_player',
                    predicted_home_margin=(home_df['predicted_margin']
                                           .round()),
                    home_margin=home_df['score'] - home_df['oppo_score'],
                    predicted_home_win=((home_df['predicted_margin'] > 0)
                                        .astype(int)),
                    home_win=((home_df['score'] > home_df['oppo_score'])
                              .astype(int)),
                    draw=(home_df['score'] == home_df['oppo_score']).astype(int))
            .assign(tip_point=lambda x: ((x['predicted_home_win'] == x['home_win']) |
                                         (x['draw'])).astype(int))
            .reset_index(drop=True))


def tipresias_match_predictions() -> pd.DataFrame:
    """Generate prediction data frame for estimator based on match data

    Returns:
        pandas.DataFrame
    """

    data = MatchXGBData(train_years=(None, None), test_years=(None, None))
    estimator = MatchXGB()

    predictions = []

    for test_year in range(2011, 2017):
        data.train_years = (0, test_year - 1)
        data.test_years = (test_year, test_year)

        estimator.fit(*data.train_data())
        y_pred = estimator.predict(data.test_data()[0])

        predictions.append(y_pred)

    pred_col = pd.concat(predictions)

    pred_df = pd.concat([data.data, pred_col], join='inner', axis=1)
    home_df = pred_df[pred_df['at_home'] == 1]

    return (home_df.loc[:, ['year', 'round_number', 'team', 'oppo_team']]
            .rename(columns={'team': 'home_team', 'oppo_team': 'away_team'})
            .assign(model='tipresias_match',
                    predicted_home_margin=(home_df['predicted_margin']
                                           .round()),
                    home_margin=home_df['score'] - home_df['oppo_score'],
                    predicted_home_win=((home_df['predicted_margin'] > 0)
                                        .astype(int)),
                    home_win=((home_df['score'] > home_df['oppo_score'])
                              .astype(int)),
                    draw=(home_df['score'] == home_df['oppo_score']).astype(int))
            .assign(tip_point=lambda x: ((x['predicted_home_win'] == x['home_win']) |
                                         (x['draw'])).astype(int))
            .reset_index(drop=True))


def tipresias_betting_predictions() -> pd.DataFrame:
    """Generate prediction data frame for estimator based on betting data

    Returns:
        pandas.DataFrame
    """

    data = BettingLassoData(train_years=(None, None), test_years=(None, None))
    estimator = BettingLasso()

    predictions = []

    for test_year in range(2011, 2017):
        data.train_years = (0, test_year - 1)
        data.test_years = (test_year, test_year)

        estimator.fit(*data.train_data())
        y_pred = estimator.predict(data.test_data()[0])

        predictions.append(y_pred)

    pred_col = pd.concat(predictions)

    pred_df = pd.concat([data.data, pred_col], join='inner', axis=1)
    home_df = pred_df[pred_df['at_home'] == 1]

    return (home_df.loc[:, ['year', 'round_number', 'team', 'oppo_team']]
            .rename(columns={'team': 'home_team', 'oppo_team': 'away_team'})
            .assign(model='tipresias_betting',
                    predicted_home_margin=(home_df['predicted_margin']
                                           .round()),
                    home_margin=home_df['score'] - home_df['oppo_score'],
                    predicted_home_win=((home_df['predicted_margin'] > 0)
                                        .astype(int)),
                    home_win=((home_df['score'] > home_df['oppo_score'])
                              .astype(int)),
                    draw=(home_df['score'] == home_df['oppo_score']).astype(int))
            .assign(tip_point=lambda x: ((x['predicted_home_win'] == x['home_win']) |
                                         (x['draw'])).astype(int))
            .reset_index(drop=True))


def oddsmakers_predictions() -> pd.DataFrame:
    """Generate prediction data frame based on raw betting odds

    Args:
        df (pandas.DataFrame): Cleaned betting & match data.

    Returns:
        pandas.DataFrame
    """

    csv_paths = [f'data/{data_file}' for data_file in DATA_FILES]
    data_classes = (BettingData, MatchData)

    raw_df = DataBuilder(data_classes, csv_paths).concat()
    transformer = DataTransformer(raw_df)

    df = transformer.clean()

    # Get predictions after 2010, because betting data starts in 2010, so associated
    # models can only start predicting for 2011 season
    return (df[df['year'] > 2010]
            .loc[:, ['year', 'round_number', 'home_team', 'away_team']]
            .assign(model='oddsmakers',
                    # Rounding predicted margin, because you can't actually
                    # predict fractions of a point
                    predicted_home_margin=df['home_line_odds'].round() * -1,
                    home_margin=df['home_score'] - df['away_score'],
                    predicted_home_win=(((df['home_win_odds'] < df['away_win_odds']) |
                                         (df['home_line_odds'] < df['away_line_odds']) |
                                         # If odds are all equal, predict home team
                                         ((df['home_win_odds'] == df['away_win_odds']) &
                                          (df['home_line_odds'] == df['away_line_odds'])))
                                        .astype(int)),
                    home_win=(df['home_score'] >
                              df['away_score']).astype(int),
                    draw=(df['home_score'] == df['away_score']).astype(int))
            .assign(tip_point=lambda x: ((x['predicted_home_win'] == x['home_win']) |
                                         (x['draw'])).astype(int)))


def main():
    pd.concat([
        oddsmakers_predictions(),
        tipresias_betting_predictions(),
        tipresias_match_predictions(),
        tipresias_player_predictions()
    ]).to_csv(f'{PROJECT_PATH}/data/model_predictions.csv', index=False)


if __name__ == '__main__':
    main()
