from unittest import TestCase
from faker import Faker
import pandas as pd

from machine_learning.data_processors.feature_calculation import (
    feature_calculator,
    calculate_rolling_rate,
    calculate_division,
    calculate_multiplication,
    calculate_rolling_mean_by_dimension,
    calculate_addition,
)
from tests.fixtures.data_factories import fake_cleaned_match_data

FAKE = Faker()
ROW_COUNT = 10
YEAR_RANGE = (2015, 2016)


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
        self.data_frame = fake_cleaned_match_data(ROW_COUNT, YEAR_RANGE)

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

    def test_calculate_addition(self):
        calc_function = calculate_addition(("score", "oppo_score"))

        assert_required_columns(
            self,
            req_cols=("score", "oppo_score"),
            valid_data_frame=self.data_frame,
            feature_function=calc_function,
        )

        addition_scores = calc_function(self.data_frame)
        self.assertIsInstance(addition_scores, pd.Series)
        self.assertEqual(addition_scores.name, "score_plus_oppo_score")
