import os
import sys
from unittest import TestCase
from faker import Faker
import pandas as pd
import numpy as np

PROJECT_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '../../../')
)

if PROJECT_PATH not in sys.path:
    sys.path.append(PROJECT_PATH)

from server.data_processors.feature_functions import (
    add_last_week_result,
    add_last_week_score,
    add_cum_percent,
    add_cum_win_points,
    add_rolling_pred_win_rate,
    add_rolling_last_week_win_rate,
    add_ladder_position,
    add_win_streak
)

FAKE = Faker()


def assert_column_added(test_case, column_name='', valid_data_frame=None,
                        feature_function=None):
    with test_case.subTest(data_frame=valid_data_frame):
        data_frame = valid_data_frame
        transformed_data_frame = feature_function(data_frame)

        test_case.assertEqual(len(data_frame.columns) + 1,
                              len(transformed_data_frame.columns))
        test_case.assertIn(column_name, transformed_data_frame.columns)


def assert_required_columns(test_case, req_cols=[], valid_data_frame=None,
                            feature_function=None):
    for req_col in req_cols:
        with test_case.subTest(data_frame=valid_data_frame.drop(req_col, axis=1)):
            data_frame = valid_data_frame.drop(req_col, axis=1)
            with test_case.assertRaises(ValueError):
                feature_function(data_frame)


def make_column_assertions(test_case, column_name='', req_cols=[],
                           valid_data_frame=None, feature_function=None):
    assert_column_added(
        test_case,
        column_name=column_name,
        valid_data_frame=valid_data_frame,
        feature_function=feature_function
    )

    assert_required_columns(
        test_case,
        req_cols=req_cols,
        valid_data_frame=valid_data_frame,
        feature_function=feature_function
    )


class TestFeatureFunctions(TestCase):
    def setUp(self):
        teams = [FAKE.company() for _ in range(10)]
        oppo_teams = list(reversed(teams))

        self.data_frame = pd.DataFrame({
            'team': teams,
            'oppo_team': oppo_teams,
            'year': [2015 for _ in range(10)],
            'round_number': [3 for _ in range(10)],
            'score': np.random.randint(50, 150, 10),
            'oppo_score': np.random.randint(50, 150, 10)
        }).set_index(['year', 'round_number', 'team'], drop=False)

    def test_add_last_week_result(self):
        feature_function = add_last_week_result
        valid_data_frame = self.data_frame

        make_column_assertions(
            self,
            column_name='last_week_result',
            req_cols=('score', 'oppo_score'),
            valid_data_frame=valid_data_frame,
            feature_function=feature_function
        )

    def test_add_last_week_score(self):
        feature_function = add_last_week_score
        valid_data_frame = self.data_frame

        make_column_assertions(
            self,
            column_name='last_week_score',
            req_cols=('score', 'oppo_score'),
            valid_data_frame=valid_data_frame,
            feature_function=feature_function
        )

    def test_add_cum_percent(self):
        feature_function = add_cum_percent
        valid_data_frame = self.data_frame.assign(
            last_week_score=np.random.randint(50, 150, 10),
            oppo_last_week_score=np.random.randint(50, 150, 10)
        )

        make_column_assertions(
            self,
            column_name='cum_percent',
            req_cols=('last_week_score', 'oppo_last_week_score'),
            valid_data_frame=valid_data_frame,
            feature_function=feature_function
        )

    def test_add_cum_win_points(self):
        feature_function = add_cum_win_points
        valid_data_frame = self.data_frame.assign(
            last_week_result=np.random.randint(0, 2, 10)
        )

        make_column_assertions(
            self,
            column_name='cum_win_points',
            req_cols=('last_week_result',),
            valid_data_frame=valid_data_frame,
            feature_function=feature_function
        )

    def test_add_rolling_pred_win_rate(self):
        feature_function = add_rolling_pred_win_rate
        valid_data_frame = self.data_frame.assign(
            # Random float from 1 to 4 covers most odds values
            win_odds=(3 * np.random.ranf(10)) + 1,
            oppo_win_odds=(3 * np.random.ranf(10)) + 1,
            line_odds=np.random.randint(-30, 30, 10),
            oppo_line_odds=np.random.randint(-30, 30, 10)
        )

        make_column_assertions(
            self,
            column_name='rolling_pred_win_rate',
            req_cols=('win_odds', 'oppo_win_odds',
                      'line_odds', 'oppo_line_odds'),
            valid_data_frame=valid_data_frame,
            feature_function=feature_function
        )

    def test_add_rolling_last_week_win_rate(self):
        feature_function = add_rolling_last_week_win_rate
        valid_data_frame = self.data_frame.assign(
            last_week_result=np.random.randint(0, 2, 10)
        )

        make_column_assertions(
            self,
            column_name='rolling_last_week_win_rate',
            req_cols=('last_week_result',),
            valid_data_frame=valid_data_frame,
            feature_function=feature_function
        )

    def test_add_ladder_position(self):
        feature_function = add_ladder_position
        valid_data_frame = self.data_frame.assign(
            # Float from 0.5 to 2.0 covers most percentages
            cum_percent=(2.5 * np.random.ranf(10)) - 0.5,
            cum_win_points=np.random.randint(0, 60, 10)
        )

        make_column_assertions(
            self,
            column_name='ladder_position',
            req_cols=('cum_percent', 'cum_win_points',
                      'team', 'year', 'round_number'),
            valid_data_frame=valid_data_frame,
            feature_function=feature_function
        )

    def test_add_win_streak(self):
        feature_function = add_win_streak
        valid_data_frame = self.data_frame.assign(
            last_week_result=np.random.randint(0, 2, 10)
        )

        make_column_assertions(
            self,
            column_name='win_streak',
            req_cols=('last_week_result',),
            valid_data_frame=valid_data_frame,
            feature_function=feature_function
        )
