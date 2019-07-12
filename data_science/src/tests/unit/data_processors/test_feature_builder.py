from unittest import TestCase
from faker import Faker

from machine_learning.data_processors import FeatureBuilder
from tests.fixtures.data_factories import fake_cleaned_match_data

FAKE = Faker()
MATCH_COUNT_PER_YEAR = 10
YEAR_RANGE = (2015, 2016)
# Need to multiply by two, because we add team & oppo_team row per match
ROW_COUNT = MATCH_COUNT_PER_YEAR * len(range(*YEAR_RANGE)) * 2


class TestFeatureBuilder(TestCase):
    def setUp(self):
        feature_funcs = [
            lambda df: df.assign(new_col=[FAKE.name() for _ in range(ROW_COUNT)]),
            lambda df: df.assign(newer_col=df["new_col"] + " but even newer"),
        ]
        self.builder = FeatureBuilder(feature_funcs=feature_funcs)

    def test_transform(self):
        valid_data_frame = fake_cleaned_match_data(MATCH_COUNT_PER_YEAR, YEAR_RANGE)

        with self.subTest(data_frame=valid_data_frame):
            data_frame = valid_data_frame

            transformed_df = self.builder.transform(data_frame)

            # FeatureBuilder adds 1 column per function
            self.assertEqual(len(data_frame.columns) + 2, len(transformed_df.columns))

            # Should add the two new columns and their 'oppo_' equivalents
            self.assertIn("new_col", transformed_df.columns)
            self.assertIn("newer_col", transformed_df.columns)

        for required_col in self.builder.index_cols:
            with self.subTest(data_frame=valid_data_frame.drop(required_col, axis=1)):
                data_frame = valid_data_frame.drop(required_col, axis=1)

                with self.assertRaises(ValueError):
                    self.builder.transform(data_frame)
