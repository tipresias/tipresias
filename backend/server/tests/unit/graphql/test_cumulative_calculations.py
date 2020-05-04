# pylint: disable=missing-docstring
from django.test import TestCase
import pandas as pd
from faker import Faker
import numpy as np
import pytz

from server.graphql.cumulative_calculations import (
    consolidate_competition_predictions,
    filter_by_round,
    calculate_cumulative_metrics,
)


FAKE = Faker()
ROUND_COUNT = 4
MATCH_COUNT = 3
YEAR_RANGE = (2014, 2016)
MODEL_NAMES = ["predictanator", "accurate_af"]


# TODO: Refactor test_schema to move tests of cumulative metric calculations here,
# so that module can focus on query logic. Until then, this will just be duplicating
# testing that is already occurring elsewhere.
class TestCumulativeCalculations(TestCase):
    def test_consolidate_competition_predictions(self):
        match_count = np.random.randint(9)

        match_predictions = []

        for idx in range(match_count):
            match_predictions.extend(
                [
                    {
                        "match__id": idx,
                        "ml_model__is_principle": True,
                        "ml_model__used_in_competitions": True,
                        "cumulative_mean_absolute_error": np.random.uniform(20, 40),
                        "cumulative_margin_difference": np.random.randint(100, 200),
                        "cumulative_bits": None,
                        "predicted_margin": np.random.randint(1, 50),
                        "predicted_win_probability": None,
                        "predicted_winner": FAKE.company(),
                    },
                    {
                        "match__id": idx,
                        "ml_model__is_principle": False,
                        "ml_model__used_in_competitions": True,
                        "cumulative_mean_absolute_error": None,
                        "cumulative_margin_difference": None,
                        "cumulative_bits": np.random.uniform(1, 15),
                        "predicted_margin": None,
                        "predicted_win_probability": np.random.uniform(0.51, 0.99),
                        "predicted_winner": FAKE.company(),
                    },
                ]
            )

        data_frame = pd.DataFrame(match_predictions)
        consolidated_data_frame = consolidate_competition_predictions(data_frame)

        # Has one set of metrics
        self.assertEqual(len(consolidated_data_frame), match_count)
        # Fills all NaNs
        self.assertFalse(consolidated_data_frame.isna().any().any())
        # Uses principle model for team predictions
        self.assertTrue(
            (
                consolidated_data_frame["predicted_winner"].reset_index(drop=True)
                == data_frame.query("ml_model__is_principle == True")[
                    "predicted_winner"
                ].reset_index(drop=True)
            ).all()
        )
        # Doesn't include any neutral values
        self.assertTrue(
            (consolidated_data_frame["cumulative_mean_absolute_error"] > 0).all()
        )
        self.assertTrue(
            (consolidated_data_frame["cumulative_margin_difference"] > 0).all()
        )
        self.assertTrue((consolidated_data_frame["cumulative_bits"] != 0).all())
        self.assertTrue((consolidated_data_frame["predicted_margin"] > 0).all())
        self.assertTrue(
            (consolidated_data_frame["predicted_win_probability"] > 0.5).all()
        )

        with self.subTest("when some non-competition models are included"):
            invalid_data_frame = data_frame.assign(ml_model__used_in_competitions=False)

            with self.assertRaises(AssertionError):
                consolidate_competition_predictions(invalid_data_frame)

    def test_filter_by_round(self):
        min_range = 2
        max_range = 25
        round_count = np.random.randint(min_range, max_range)

        data_frame = pd.DataFrame(
            [
                {
                    "match__round_number": idx,
                    "ml_model__name": FAKE.company(),
                    "metric": np.random.rand(),
                }
                for idx in range(round_count)
            ]
        ).set_index(["match__round_number", "ml_model__name"])

        filter_round_number = np.random.randint(round_count)
        filtered_data_frame = filter_by_round(data_frame, filter_round_number)

        round_numbers = filtered_data_frame.index.get_level_values(0)

        # Only has one round
        self.assertEqual(len(round_numbers.drop_duplicates()), 1)
        # Only has the round given
        self.assertEqual(round_numbers[0], filter_round_number)

        with self.subTest("when round_number arg is blank"):
            filtered_data_frame = filter_by_round(data_frame)

            # Includes all rounds
            self.assertEqual(len(filtered_data_frame), len(data_frame))

        with self.subTest("when round_number is -1"):
            filtered_data_frame = filter_by_round(data_frame, -1)

            # Only has last round
            self.assertEqual(
                filtered_data_frame.index.get_level_values(0)[0],
                data_frame.index.get_level_values(0).max(),
            )

    def test_calculate_cumulative_metrics(self):
        round_count = np.random.randint(1, 5)
        match_count = np.random.randint(9)
        ml_models = ["predictinator", "accurate_af"]

        match_predictions = []

        for round_idx in range(round_count):
            for _ in range(match_count):
                teams = [FAKE.company(), FAKE.company()]
                match_winner = np.random.choice(teams)
                match_margin_diff = np.random.randint(1, 50)

                match_predictions.extend(
                    [
                        {
                            "match__start_date_time": FAKE.date_time(tzinfo=pytz.UTC),
                            "match__round_number": round_idx,
                            "ml_model__name": ml_models[0],
                            "ml_model__is_principle": True,
                            "ml_model__used_in_competitions": True,
                            "predicted_margin": np.random.randint(1, 50),
                            "predicted_win_probability": None,
                            "predicted_winner__name": np.random.choice(teams),
                            "match__winner__name": match_winner,
                            "absolute_margin_diff": match_margin_diff,
                            "cumulative_correct_count": np.random.randint(1, 10)
                            * round_idx,
                            "cumulative_accuracy": np.random.rand(),
                        },
                        {
                            "match__start_date_time": FAKE.date_time(tzinfo=pytz.UTC),
                            "match__round_number": round_idx,
                            "ml_model__name": ml_models[1],
                            "ml_model__is_principle": False,
                            "ml_model__used_in_competitions": True,
                            "predicted_margin": None,
                            "predicted_win_probability": np.random.uniform(0.51, 0.99),
                            "predicted_winner__name": np.random.choice(teams),
                            "match__winner__name": match_winner,
                            "absolute_margin_diff": match_margin_diff,
                            "cumulative_correct_count": np.random.randint(1, 10)
                            * round_idx,
                            "cumulative_accuracy": np.random.rand(),
                        },
                    ]
                )

        data_frame = calculate_cumulative_metrics(match_predictions)

        # Has cumulative metrics
        calculated_metrics = set(
            [
                "cumulative_margin_difference",
                "cumulative_bits",
                "cumulative_mean_absolute_error",
            ]
        )
        self.assertEqual(
            calculated_metrics, calculated_metrics & set(data_frame.columns)
        )

    def test_query_database_for_prediction_metrics(self):
        # Waiting on a refactor of GQL-related tests, see comment at top of class.
        pass
