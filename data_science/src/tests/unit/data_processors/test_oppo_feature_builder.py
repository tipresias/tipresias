from collections import Counter
from unittest import TestCase
from faker import Faker
import numpy as np

from machine_learning.data_processors import OppoFeatureBuilder
from machine_learning.data_processors.oppo_feature_builder import REQUIRED_COLS
from tests.fixtures.data_factories import fake_cleaned_match_data

FAKE = Faker()
N_ROWS_PER_YEAR = 10
YEAR_RANGE = (2015, 2016)
# Need to multiply by two, because we add team & oppo_team row per match
N_ROWS = N_ROWS_PER_YEAR * len(range(*YEAR_RANGE)) * 2


class TestOppoFeatureBuilder(TestCase):
    def setUp(self):
        self.match_cols = [
            "date",
            "team",
            "oppo_team",
            "score",
            "oppo_score",
            "year",
            "round_number",
        ]
        self.oppo_feature_cols = ["kicks", "marks"]
        self.builder = OppoFeatureBuilder
        self.data_frame = fake_cleaned_match_data(N_ROWS_PER_YEAR, YEAR_RANGE).assign(
            kicks=np.random.randint(50, 100, N_ROWS),
            marks=np.random.randint(50, 100, N_ROWS),
        )

    def test_transform(self):
        valid_data_frame = self.data_frame

        with self.subTest(data_frame=valid_data_frame, match_cols=self.match_cols):
            data_frame = valid_data_frame
            match_cols = self.match_cols
            transformed_df = self.builder(match_cols=match_cols).transform(data_frame)

            # OppoFeatureBuilder adds 1 column per non-match column
            self.assertEqual(len(data_frame.columns) + 2, len(transformed_df.columns))

            # Should add the two new oppo columns
            self.assertIn("oppo_kicks", transformed_df.columns)
            self.assertIn("oppo_marks", transformed_df.columns)

            # Shouldn't add the match columns
            for match_col in match_cols:
                if match_col not in ["team", "score"]:
                    self.assertNotIn(f"oppo_{match_col}", transformed_df.columns)

            self.assertEqual(Counter(transformed_df.columns)["oppo_team"], 1)
            self.assertEqual(Counter(transformed_df.columns)["oppo_score"], 1)

            # Columns & their 'oppo_' equivalents should have the same values
            self.assertEqual(
                len(
                    np.setdiff1d(transformed_df["kicks"], transformed_df["oppo_kicks"])
                ),
                0,
            )
            self.assertEqual(
                len(
                    np.setdiff1d(transformed_df["marks"], transformed_df["oppo_marks"])
                ),
                0,
            )

        with self.subTest(
            data_frame=valid_data_frame, oppo_feature_cols=self.oppo_feature_cols
        ):
            data_frame = valid_data_frame
            oppo_feature_cols = self.oppo_feature_cols
            transformed_df = self.builder(
                oppo_feature_cols=oppo_feature_cols
            ).transform(data_frame)

            # OppoFeatureBuilder adds 1 column per non-match column
            self.assertEqual(len(data_frame.columns) + 2, len(transformed_df.columns))

            # Should add the two new oppo columns
            self.assertIn("oppo_kicks", transformed_df.columns)
            self.assertIn("oppo_marks", transformed_df.columns)

            # Shouldn't add the match columns
            for match_col in self.match_cols:
                if match_col not in ["team", "score"]:
                    self.assertNotIn(f"oppo_{match_col}", transformed_df.columns)

            self.assertEqual(Counter(transformed_df.columns)["oppo_team"], 1)
            self.assertEqual(Counter(transformed_df.columns)["oppo_score"], 1)

            # Columns & their 'oppo_' equivalents should have the same values
            self.assertEqual(
                len(
                    np.setdiff1d(transformed_df["kicks"], transformed_df["oppo_kicks"])
                ),
                0,
            )
            self.assertEqual(
                len(
                    np.setdiff1d(transformed_df["marks"], transformed_df["oppo_marks"])
                ),
                0,
            )

        with self.subTest(
            match_cols=self.match_cols, oppo_feature_cols=self.oppo_feature_cols
        ):
            with self.assertRaises(ValueError):
                (
                    self.builder(
                        match_cols=self.match_cols,
                        oppo_feature_cols=self.oppo_feature_cols,
                    ).transform(self.data_frame)
                )

        for required_col in REQUIRED_COLS:
            with self.subTest(data_frame=valid_data_frame.drop(required_col, axis=1)):
                data_frame = valid_data_frame.drop(required_col, axis=1)

                with self.assertRaises(ValueError):
                    (self.builder(match_cols=self.match_cols).transform(data_frame))
