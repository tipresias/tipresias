import os
import pandas as pd
from notebooks.src.data.data_builder import DataBuilder, BettingData, MatchData
from notebooks.src.data.data_transformer import DataTransformer

project_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../'))

DATA_FILES = ('afl_betting.csv', 'ft_match_list.csv')


def oddsmakers_predictions(df):
    return (df.loc[:, ['year', 'round_number', 'home_team', 'away_team']]
              .assign(model='oddsmakers',
                      predicted_home_margin=df['home_line_odds'] * -1,
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
    data_df = DataTransformer(raw_df).clean()
    prediction_df(data_df).to_csv(f'{project_path}/data/model_predictions.csv',
                                  index=False)
