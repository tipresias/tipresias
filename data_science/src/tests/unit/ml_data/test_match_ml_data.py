from unittest import TestCase
from unittest.mock import Mock
from datetime import date
import os
import pandas as pd
from faker import Faker

from machine_learning.settings import BASE_DIR, MELBOURNE_TIMEZONE

from machine_learning.ml_data import MatchMLData

FAKE = Faker()

match_results_df = pd.read_csv(
    os.path.join(BASE_DIR, "src/tests/fixtures/fitzroy_match_results.csv")
).assign(date=lambda df: pd.to_datetime(df["date"]).dt.tz_localize(MELBOURNE_TIMEZONE))
match_results_mock = Mock(return_value=match_results_df)

fixture_df = pd.read_csv(
    os.path.join(BASE_DIR, "src/tests/fixtures/ft_match_list.csv")
).assign(date=lambda df: pd.to_datetime(df["date"]).dt.tz_localize(MELBOURNE_TIMEZONE))
fixture_mock_df = (
    fixture_df.sort_values("date", ascending=False)
    .iloc[:10, :]
    .drop_duplicates(subset="round")
    .assign(
        date=FAKE.date_time_this_month(
            after_now=True, before_now=False, tzinfo=MELBOURNE_TIMEZONE
        )
    )
)
# Try to grab one round's worth of match data and change date to be in the future to mock
# fetching data for upcoming round
fixture_mock = Mock(return_value=fixture_mock_df)


class TestMatchMLData(TestCase):
    def setUp(self):
        self.data = MatchMLData(
            data_readers={
                "match": (match_results_mock, {}),
                "fixture": (fixture_mock, {}),
            }
        )

    def test_fetch_data(self):
        fetched_data = MatchMLData(
            data_readers={
                "match": (match_results_mock, {}),
                "fixture": (fixture_mock, {}),
            },
            fetch_data=True,
        )
        current_year = date.today().year

        self.assertTrue(current_year in fetched_data.data["year"].values)

    def test_train_data(self):
        X_train, y_train = self.data.train_data()

        self.assertIsInstance(X_train, pd.DataFrame)
        self.assertIsInstance(y_train, pd.Series)
        self.assertNotIn("score", X_train.columns)
        self.assertNotIn("oppo_score", X_train.columns)
        self.assertNotIn("team_goals", X_train.columns)
        self.assertNotIn("oppo_team_goals", X_train.columns)
        self.assertNotIn("team_behinds", X_train.columns)
        self.assertNotIn("oppo_team_behinds", X_train.columns)
        self.assertNotIn("margin", X_train.columns)
        self.assertNotIn("result", X_train.columns)

        # Applying StandardScaler to integer columns raises a warning
        self.assertFalse(
            any([X_train[column].dtype == int for column in X_train.columns])
        )

    def test_test_data(self):
        X_test, y_test = self.data.test_data()

        self.assertIsInstance(X_test, pd.DataFrame)
        self.assertIsInstance(y_test, pd.Series)
        self.assertNotIn("score", X_test.columns)
        self.assertNotIn("oppo_score", X_test.columns)
        self.assertNotIn("team_goals", X_test.columns)
        self.assertNotIn("oppo_team_goals", X_test.columns)
        self.assertNotIn("team_behinds", X_test.columns)
        self.assertNotIn("oppo_team_behinds", X_test.columns)
        self.assertNotIn("result", X_test.columns)

        # Applying StandardScaler to integer columns raises a warning
        self.assertFalse(
            any([X_test[column].dtype == int for column in X_test.columns])
        )

    def test_train_test_data_compatibility(self):
        self.maxDiff = None

        X_train, _ = self.data.train_data()
        X_test, _ = self.data.test_data()

        self.assertCountEqual(list(X_train.columns), list(X_test.columns))
