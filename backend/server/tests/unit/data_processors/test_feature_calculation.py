from unittest import TestCase
from faker import Faker
import pandas as pd
import numpy as np

from server.data_processors.feature_calculation import (
    feature_calculator,
    calculate_rolling_rate,
    calculate_division,
    calculate_multiplication,
    calculate_rolling_mean_by_dimension,
)

FAKE = Faker()


def assert_required_columns(
    test_case, req_cols=[], valid_data_frame=None, feature_function=None
):
    for req_col in req_cols:
        with test_case.subTest(data_frame=valid_data_frame.drop(req_col, axis=1)):
            data_frame = valid_data_frame.drop(req_col, axis=1)
            with test_case.assertRaises(ValueError):
                feature_function(data_frame)


class TestFeatureCalculations(TestCase):
    def setUp(self):
        teams = [FAKE.company() for _ in range(10)]
        oppo_teams = list(reversed(teams))

        self.data_frame = (
            pd.DataFrame(
                {
                    "team": teams,
                    "oppo_team": oppo_teams,
                    "year": [2015 for _ in range(10)],
                    "round_number": [3 for _ in range(5)] + [4 for _ in range(5)],
                    "score": np.random.randint(50, 150, 10),
                    "oppo_score": np.random.randint(50, 150, 10),
                }
            )
            .set_index(["team", "year", "round_number"], drop=False)
            .rename_axis([None, None, None])
        )

    def test_feature_calculator(self):
        def calc_func(col):
            return lambda df: df[col].rename(f"new_{col}")

        calculators = [
            (calc_func, ["team", "year"]),
            (calc_func, ["round_number", "score"]),
        ]
        calc_function = feature_calculator(calculators)
        calculated_data_frame = calc_function(self.data_frame)

        self.assertIsInstance(calculated_data_frame, pd.DataFrame)
        self.assertFalse(any(calculated_data_frame.columns.duplicated()))

    def test_calculate_rolling_rate(self):
        calc_function = calculate_rolling_rate(("score",))

        assert_required_columns(
            self,
            req_cols=("score",),
            valid_data_frame=self.data_frame,
            feature_function=calc_function,
        )

        rolling_score = calc_function(self.data_frame)
        self.assertIsInstance(rolling_score, pd.Series)
        self.assertEqual(rolling_score.name, "rolling_score_rate")

    def test_calculate_division(self):
        calc_function = calculate_division(("score", "oppo_score"))

        assert_required_columns(
            self,
            req_cols=("score", "oppo_score"),
            valid_data_frame=self.data_frame,
            feature_function=calc_function,
        )

        divided_scores = calc_function(self.data_frame)
        self.assertIsInstance(divided_scores, pd.Series)
        self.assertEqual(divided_scores.name, "score_divided_by_oppo_score")

    def test_calculate_multiplication(self):
        calc_function = calculate_multiplication(("score", "oppo_score"))

        assert_required_columns(
            self,
            req_cols=("score", "oppo_score"),
            valid_data_frame=self.data_frame,
            feature_function=calc_function,
        )

        multiplied_scores = calc_function(self.data_frame)
        self.assertIsInstance(multiplied_scores, pd.Series)
        self.assertEqual(multiplied_scores.name, "score_multiplied_by_oppo_score")

    def test_calculate_rolling_mean_by_dimension(self):
        calc_function = calculate_rolling_mean_by_dimension(("oppo_team", "score"))

        assert_required_columns(
            self,
            req_cols=("oppo_team", "score"),
            valid_data_frame=self.data_frame,
            feature_function=calc_function,
        )

        rolling_oppo_team_score = calc_function(self.data_frame)
        self.assertIsInstance(rolling_oppo_team_score, pd.Series)
        self.assertEqual(
            rolling_oppo_team_score.name, "rolling_mean_score_by_oppo_team"
        )
