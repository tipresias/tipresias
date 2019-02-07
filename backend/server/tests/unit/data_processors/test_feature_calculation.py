from unittest import TestCase
from faker import Faker
import pandas as pd
import numpy as np

from server.data_processors.feature_calculation import (
    feature_calculator,
    calculate_rolling_rate,
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
        calculators = [
            (lambda col: lambda df: df[col].rename(f"new_{col}"), ["team", "year"]),
            (
                lambda col: lambda df: df[col].rename(f"new_{col}"),
                ["round_number", "score"],
            ),
        ]
        calc_function = feature_calculator(calculators)
        calculated_data_frame = calc_function(self.data_frame)

        self.assertIsInstance(calculated_data_frame, pd.DataFrame)
        self.assertFalse(any(calculated_data_frame.columns.duplicated()))

    def test_calculate_rolling_rate(self):
        calc_function = calculate_rolling_rate("score")

        assert_required_columns(
            self,
            req_cols=("score",),
            valid_data_frame=self.data_frame,
            feature_function=calc_function,
        )

        rolling_score = calc_function(self.data_frame)
        self.assertIsInstance(rolling_score, pd.Series)
        self.assertEqual(rolling_score.name, "rolling_score_rate")
