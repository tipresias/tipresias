from unittest import TestCase
from faker import Faker
import pandas as pd
import numpy as np

from server.data_processors import TeamDataStacker

FAKE = Faker()


class TestTeamDataStacker(TestCase):
    def setUp(self):
        self.transformer = TeamDataStacker()

    def test_transform(self):
        # DataFrame w/ minimum valid columns
        valid_data_frame = pd.DataFrame(
            {
                "home_team": [FAKE.company() for _ in range(10)],
                "away_team": [FAKE.company() for _ in range(10)],
                "year": [FAKE.year() for _ in range(10)],
                "round_number": [np.random.randint(1, 24) for _ in range(10)],
                "home_score": [np.random.randint(50, 150) for _ in range(10)],
                "away_score": [np.random.randint(50, 150) for _ in range(10)],
            }
        )

        invalid_data_frame = pd.DataFrame(
            {
                "home_team": [FAKE.company() for _ in range(10)],
                "away_team": [FAKE.company() for _ in range(10)],
                "round_number": [np.random.randint(1, 24) for _ in range(10)],
                "home_score": [np.random.randint(50, 150) for _ in range(10)],
                "away_score": [np.random.randint(50, 150) for _ in range(10)],
            }
        )

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
