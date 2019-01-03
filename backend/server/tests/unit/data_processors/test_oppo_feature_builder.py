from collections import Counter
from unittest import TestCase
from faker import Faker
import pandas as pd
import numpy as np

from server.data_processors import OppoFeatureBuilder
from server.data_processors.oppo_feature_builder import REQUIRED_COLS

FAKE = Faker()


class TestOppoFeatureBuilder(TestCase):
    def setUp(self):
        self.match_cols = [
            "team",
            "oppo_team",
            "score",
            "oppo_score",
            "year",
            "round_number",
        ]
        self.oppo_feature_cols = ["kicks", "marks"]
        self.builder = OppoFeatureBuilder

        teams = [FAKE.company() for _ in range(10)]
        oppo_teams = list(reversed(teams))
        self.data_frame = (
            pd.DataFrame(
                {
                    "team": teams,
                    "oppo_team": oppo_teams,
                    "year": [2015 for _ in range(10)],
                    "round_number": [3 for _ in range(10)],
                    "score": np.random.randint(50, 150, 10),
                    "oppo_score": np.random.randint(50, 150, 10),
                    "kicks": np.random.randint(50, 100, 10),
                    "marks": np.random.randint(50, 100, 10),
                }
            )
            .set_index(["year", "round_number", "team"], drop=False)
            .rename_axis([None, None, None])
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
