import os
import sys
import pandas as pd
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import Lasso

project_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../'))
if project_path not in sys.path:
    sys.path.append(project_path)

from notebooks.src.data.data_builder import DataBuilder, BettingData, MatchData
from notebooks.src.data.data_transformer import DataTransformer
from notebooks.src.data.feature_builder import FeatureBuilder

DATA_FILES = ('afl_betting.csv', 'ft_match_list.csv')


def tipresias_betting_predictions(df):
    fb = FeatureBuilder(df)
    fb.transform()
    team_df = fb.df.dropna()

    team_features = pd.get_dummies(
        team_df.drop(['score', 'oppo_score'], axis=1))
    team_labels = pd.Series(
        team_df['score'] - team_df['oppo_score'], name='score_diff')

    estimator = make_pipeline(StandardScaler(), Lasso())

    predictions = []

    for year in range(2011, 2017):
        X_train = team_features[team_features['year'] < year]
        X_test = team_features[team_features['year'] == year]
        y_train = team_labels.loc[X_train.index]

        estimator.fit(X_train, y_train)
        y_pred = estimator.predict(X_test)

        predictions.extend(y_pred)

    pred_df = team_df[team_df['year'] > 2010].assign(
        predicted_margin=predictions)
    home_df = pred_df[pred_df['at_home'] == 1]

    return (home_df.loc[:, ['year', 'round_number', 'team', 'oppo_team']]
            .rename(columns={'team': 'home_team', 'oppo_team': 'away_team'})
            .assign(model='tipresias_betting',
                    predicted_home_margin=home_df['predicted_margin'].round(
                    ),
                    home_margin=home_df['score'] - home_df['oppo_score'],
                    predicted_home_win=(
                        home_df['predicted_margin'] > 0).astype(int),
                    home_win=(home_df['score'] >
                              home_df['score']).astype(int),
                    draw=(home_df['score'] == home_df['score']).astype(int))
            .assign(tip_point=lambda x: ((x['predicted_home_win'] == x['home_win']) |
                                         (x['draw'])).astype(int))
            .reset_index(drop=True))


def oddsmakers_predictions(df):
    return (df.loc[:, ['year', 'round_number', 'home_team', 'away_team']]
              .assign(model='oddsmakers',
                      # Rounding predicted margin, because you can't actually predict fractions of a point
                      predicted_home_margin=df['home_line_odds'].round() * -1,
                      home_margin=df['home_score'] - df['away_score'],
                      predicted_home_win=((df['home_win_odds'] < df['away_win_odds']) |
                                          (df['home_line_odds'] < df['away_line_odds']) |
                                          # If odds are all equal, predict home team
                                          ((df['home_win_odds'] == df['away_win_odds']) &
                                           (df['home_line_odds'] == df['away_line_odds']))).astype(int),
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
        tipresias_betting_predictions(transformer.stack_teams())
    ]).to_csv(f'{project_path}/data/model_predictions.csv', index=False)


if __name__ == '__main__':
    main()
