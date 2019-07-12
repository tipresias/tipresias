from unittest import TestCase
from faker import Faker
import pandas as pd

from machine_learning.data_processors import TeamDataStacker
from tests.fixtures.data_factories import fake_cleaned_match_data

FAKE = Faker()
N_ROWS_PER_YEAR = 10
YEAR_RANGE = (2000, 2001)
# Need to multiply by two, because we add team & oppo_team row per match
N_ROWS = N_ROWS_PER_YEAR * len(range(*YEAR_RANGE)) * 2


class TestTeamDataStacker(TestCase):
    def setUp(self):
        self.transformer = TeamDataStacker()

    def test_transform(self):
        # DataFrame w/ minimum valid columns
        valid_data_frame = fake_cleaned_match_data(
            N_ROWS, YEAR_RANGE, oppo_rows=False
        ).rename(
            columns={
                "team": "home_team",
                "oppo_team": "away_team",
                "score": "home_score",
                "oppo_score": "away_score",
            }
        )

        invalid_data_frame = valid_data_frame.drop("year", axis=1)

        with self.subTest(data_frame=valid_data_frame):
            transformed_df = self.transformer.transform(valid_data_frame)

            self.assertIsInstance(transformed_df, pd.DataFrame)
            # TeamDataStacker stacks home & away teams, so the new DF should have twice as many rows
            self.assertEqual(len(valid_data_frame) * 2, len(transformed_df))
            # 'home_'/'away_' columns become regular columns or 'oppo_' columns,
            # non-team-specific columns are unchanged, and we add 'at_home'
            self.assertEqual(
                len(valid_data_frame.columns) + 1, len(transformed_df.columns)
            )
            self.assertIn("at_home", transformed_df.columns)
            # Half the teams should be marked as 'at_home'
            self.assertEqual(transformed_df["at_home"].sum(), len(transformed_df) / 2)

        with self.subTest(data_frame=invalid_data_frame):
            with self.assertRaises(ValueError):
                self.transformer.transform(invalid_data_frame)
