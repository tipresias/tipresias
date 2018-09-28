import os
import sys
import pandas as pd
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import Lasso
from sklearn.externals import joblib

project_path = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '../../'))
if project_path not in sys.path:
    sys.path.append(project_path)

from notebooks.src.data.data_builder import DataBuilder, BettingData, MatchData
from notebooks.src.data.data_transformer import DataTransformer
from notebooks.src.data.feature_builder import FeatureBuilder

DATA_FILES = ('afl_betting.csv', 'ft_match_list.csv')


def main(max_year=2016):
    csv_paths = [f'data/{data_file}' for data_file in DATA_FILES]
    data_classes = (BettingData, MatchData)

    raw_df = DataBuilder(data_classes, csv_paths).concat()
    df = DataTransformer(raw_df).stack_teams()

    fb = FeatureBuilder(df)
    fb.transform()
    team_df = fb.df.dropna()

    team_features = pd.get_dummies(
        team_df.drop(['score', 'oppo_score'], axis=1))
    team_labels = pd.Series(
        team_df['score'] - team_df['oppo_score'], name='score_diff')

    estimator = make_pipeline(StandardScaler(), Lasso())

    X_train = team_features[team_features['year'] <= max_year]
    y_train = team_labels.loc[X_train.index]

    estimator.fit(X_train, y_train)

    joblib.dump(
        estimator, f'{project_path}/app/models/betting_{estimator.steps[-1][0]}.pkl')


if __name__ == '__main__':
    main()
