import os
import sys
import pandas as pd

PROJECT_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '../../')
)
if PROJECT_PATH not in sys.path:
    sys.path.append(PROJECT_PATH)

from server.ml_models import BettingLasso
from server.ml_models.betting_lasso import BettingLassoData

from notebooks.src.data.data_builder import DataBuilder, BettingData, MatchData
from notebooks.src.data.data_transformer import DataTransformer

DATA_FILES = ('afl_betting.csv', 'ft_match_list.csv')


def tipresias_betting_predictions():
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
                    home_win=((home_df['score'] > home_df['score'])
                              .astype(int)),
                    draw=(home_df['score'] == home_df['score']).astype(int))
            .assign(tip_point=lambda x: ((x['predicted_home_win'] == x['home_win']) |
                                         (x['draw'])).astype(int))
            .reset_index(drop=True))


def oddsmakers_predictions(df):
    return (df.loc[:, ['year', 'round_number', 'home_team', 'away_team']]
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


def prediction_df(df):
    return oddsmakers_predictions(df)


def main():
    csv_paths = [f'data/{data_file}' for data_file in DATA_FILES]
    data_classes = (BettingData, MatchData)

    raw_df = DataBuilder(data_classes, csv_paths).concat()
    transformer = DataTransformer(raw_df)

    pd.concat([
        prediction_df(transformer.clean()),
        tipresias_betting_predictions()
    ]).to_csv(f'{PROJECT_PATH}/data/model_predictions.csv', index=False)


if __name__ == '__main__':
    main()
