# pylint: disable=missing-docstring

from unittest.mock import MagicMock
from dateutil import parser

from django.test import TestCase
from django.utils import timezone
import joblib
import pandas as pd

from server.models import Match, TeamMatch, Team, MLModel, Prediction
from server.management.commands import seed_db
from server.tests.fixtures.data_factories import (
    fake_match_results_data,
    fake_prediction_data,
)


MATCH_COUNT_PER_YEAR = 5


class TestSeedDb(TestCase):
    def setUp(self):
        joblib.dump = MagicMock()

        min_seed_year = int(seed_db.YEAR_RANGE.split("-")[0])
        # Min year needs to be greather than 2010, or weird stuff can happen
        # due to betting data only going back to 2010
        self.assertGreater(min_seed_year, 2010)

        # We only need a couple of valid years to test functionality
        self.years = (int(min_seed_year), int(min_seed_year + 2))
        # Need to add extra year at the beginning to provide at least one year's worth
        # of training data
        data_years = (self.years[0] - 1, self.years[1])

        self.match_results_data_frame = fake_match_results_data(
            MATCH_COUNT_PER_YEAR, data_years, clean=True
        )

        prediction_data = []

        for match_result in self.match_results_data_frame.query(
            # Only returning prediction data for matches in seed_db year range
            "year >= @min_seed_year"
        ).to_dict("records"):

            match_data = {
                "home_team": match_result["home_team"],
                "away_team": match_result["away_team"],
                "year": match_result["year"],
                "round_number": match_result["round_number"],
            }

            prediction_data.append(
                fake_prediction_data(
                    match_data=match_data, ml_model_name="test_estimator"
                )
            )

        mock_data_import = MagicMock()
        mock_data_import.fetch_match_predictions = MagicMock(
            return_value=pd.concat(prediction_data).reset_index().to_dict("records")
        )
        mock_data_import.fetch_match_results = MagicMock(
            side_effect=self.__match_results_side_effect
        )
        mock_data_import.fetch_ml_models = MagicMock(
            return_value=[
                {"name": "test_estimator", "filepath": "some/filepath/model.pkl"}
            ]
        )

        self.seed_command = seed_db.Command(
            data_importer=mock_data_import, fetch_data=False, verbose=0
        )

    def test_handle(self):
        self.seed_command.handle(year_range=f"{self.years[0]}-{self.years[1]}")

        self.assertGreater(Team.objects.count(), 0)
        self.assertEqual(MLModel.objects.count(), 1)
        self.assertEqual(
            Match.objects.count(), MATCH_COUNT_PER_YEAR * len(range(*self.years))
        )
        self.assertEqual(
            TeamMatch.objects.count(),
            MATCH_COUNT_PER_YEAR * len(range(*self.years)) * 2,
        )
        self.assertEqual(
            Prediction.objects.count(), MATCH_COUNT_PER_YEAR * len(range(*self.years))
        )
        self.assertEqual(TeamMatch.objects.filter(score=0).count(), 0)

    def test_handle_errors(self):
        with self.subTest(
            "with invalid year_range argument due to it being a single year"
        ):
            with self.assertRaises(AssertionError):
                self.seed_command.handle(year_range="2015", verbose=0)

        with self.subTest(
            "with invalid year_range argument due to years being separated by an invalid symbol"
        ):
            for symbol in [".", "_", ",", "/", "|"]:
                with self.assertRaises(AssertionError):
                    self.seed_command.handle(
                        year_range=f"{self.years[0]}{symbol}{self.years[1]}", verbose=0
                    )

    def __match_results_side_effect(
        self,
        start_date=None,
        end_date=None,
        fetch_data=False,  # pylint: disable=unused-argument
    ):
        if start_date is None or end_date is None:
            return self.match_results_data_frame.to_dict("records")

        start_datetime = timezone.make_aware(  # pylint: disable=unused-variable
            parser.parse(start_date)
        )
        end_datetime = timezone.make_aware(  # pylint: disable=unused-variable
            parser.parse(end_date)
        )

        return self.match_results_data_frame.query(
            "date >= @start_datetime & date <= @end_datetime"
        ).to_dict("records")

    @staticmethod
    def __clear_db():
        Team.objects.all().delete()
        Match.objects.all().delete()
        MLModel.objects.all().delete()
