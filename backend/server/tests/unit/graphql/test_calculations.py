# pylint: disable=missing-docstring

from django.test import TestCase
from faker import Faker
import pytest

from server.graphql import calculations


ARBITRARY_MATCH_COUNT = 5
ARBITRARY_MAX_MARGIN = 50
Fake = Faker()


class TestCalculations(TestCase):
    @pytest.mark.parametrize(
        ["round_number", "metric_value_params"],
        [
            (None, {}),
            (2, {"round_number": 2}),
            (2, {"round_number": 3}),
            (None, {"predicted_win_probability": None}),
            (None, {"predicted_margin": None}),
        ],
    )
    # @staticmethod
    def test_calculate_cumulative_metrics(self):
        expected_columns = [
            "tip_point",
            "absolute_margin_diff",
            "bits",
            "cumulative_correct_count",
            "cumulative_accuracy",
            "cumulative_margin_difference",
            "cumulative_bits",
            "cumulative_mean_absolute_error",
        ]
        metric_values = [
            {
                "match__id": n,
                "match__margin": Fake.pyint(max_value=ARBITRARY_MAX_MARGIN),
                "match__winner__name": Fake.company(),
                "match__round_number": Fake.pyint(1, 25),
                "match__start_date_time": Fake.date_time(),
                "ml_model__is_principal": Fake.pybool(),
                "ml_model__name": Fake.first_name(),
                "ml_model__used_in_competitions": Fake.pybool(),
                "predicted_margin": Fake.pyfloat(max_value=ARBITRARY_MAX_MARGIN)
                if Fake.pybool()
                else None,
                "predicted_winner__name": Fake.company(),
                "predicted_win_probability": Fake.pyfloat(0, 1)
                if Fake.pybool()
                else None,
                "is_correct": Fake.pybool(),
            }
            for n in range(ARBITRARY_MATCH_COUNT)
        ]

        cumulative_metrics = calculations.calculate_cumulative_metrics(
            metric_values, round_number=None
        )

        self.assertEqual(len(cumulative_metrics), len(metric_values))
        self.assertEqual(
            set(expected_columns) & set(cumulative_metrics.columns),
            set(expected_columns),
        )

        with self.subTest("when round_number is positive"):
            round_number = 1

            cumulative_metrics = calculations.calculate_cumulative_metrics(
                [
                    {**metric_value, "match__round_number": idx + 1}
                    for idx, metric_value in enumerate(metric_values)
                ],
                round_number,
            )

            self.assertEqual(
                set(
                    cumulative_metrics.index.get_level_values(
                        calculations.ROUND_NUMBER_LVL
                    )
                ),
                set([round_number]),
            )

        with self.subTest("when round_number is -1"):
            round_number = -1

            cumulative_metrics = calculations.calculate_cumulative_metrics(
                metric_values, round_number
            )

            self.assertEqual(
                set(
                    cumulative_metrics.index.get_level_values(
                        calculations.ROUND_NUMBER_LVL
                    )
                ),
                set([max([value["match__round_number"] for value in metric_values])]),
            )

        with self.subTest("when predicted_win_probability is all None"):
            cumulative_metrics = calculations.calculate_cumulative_metrics(
                [
                    {**metric_value, "predicted_win_probability": None}
                    for metric_value in metric_values
                ],
                round_number=None,
            )

            self.assertTrue((cumulative_metrics["cumulative_bits"] == 0).all())

        with self.subTest("when predicted_margin is all None"):
            cumulative_metrics = calculations.calculate_cumulative_metrics(
                [
                    {**metric_value, "predicted_margin": None}
                    for metric_value in metric_values
                ],
                round_number=None,
            )

            self.assertTrue(
                (cumulative_metrics["cumulative_mean_absolute_error"] == 0).all()
            )
