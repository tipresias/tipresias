import copy
from datetime import datetime, timedelta
from unittest.mock import Mock

from django.test import TestCase
from freezegun import freeze_time
import pandas as pd

from server.models import Match, TeamMatch, Prediction
from server.management.commands import tip
from server.tests.fixtures.data_factories import fake_fixture_data, fake_prediction_data
from server.tests.fixtures.factories import MLModelFactory, TeamFactory
from server import data_import


ROW_COUNT = 5

# Freezing time to make sure there is viable data, which is easier
# than mocking viable data
@freeze_time("2016-01-01")
class TestTip(TestCase):
    def setUp(self):
        tomorrow = datetime.now() + timedelta(days=1)
        year = tomorrow.year

        # Mock footywire fixture data
        fixture_data = fake_fixture_data(ROW_COUNT, (year, year + 1))

        # Mock update_or_create_from_data to make assertions on calls
        update_or_create_from_data = copy.copy(Prediction.update_or_create_from_data)
        Prediction.update_or_create_from_data = Mock(
            side_effect=self.__update_or_create_from_data(update_or_create_from_data)
        )

        MLModelFactory(name="test_estimator")

        prediction_data = []

        for match_data in fixture_data.to_dict("records"):
            TeamFactory(name=match_data["home_team"])
            TeamFactory(name=match_data["away_team"])

            prediction_data.append(
                fake_prediction_data(
                    match_data=match_data, ml_model_name="test_estimator"
                )
            )

        data_import.fetch_prediction_data = Mock(
            return_value=pd.concat(prediction_data)
        )
        data_import.fetch_fixture_data = Mock(return_value=fixture_data)

        # Not fetching data, because it takes forever
        self.tip_command = tip.Command(fetch_data=False, data_importer=data_import)

    def test_handle(self):
        with self.subTest("with no existing match records in DB"):
            self.assertEqual(Match.objects.count(), 0)
            self.assertEqual(TeamMatch.objects.count(), 0)
            self.assertEqual(Prediction.objects.count(), 0)

            self.tip_command.handle(verbose=0)

            self.assertEqual(Match.objects.count(), ROW_COUNT)
            self.assertEqual(TeamMatch.objects.count(), ROW_COUNT * 2)
            self.assertEqual(Prediction.objects.count(), ROW_COUNT)

        with self.subTest("with the match records already saved in the DB"):
            self.assertEqual(Match.objects.count(), ROW_COUNT)
            self.assertEqual(TeamMatch.objects.count(), ROW_COUNT * 2)
            self.assertEqual(Prediction.objects.count(), ROW_COUNT)

            self.tip_command.handle(verbose=0)

            Prediction.update_or_create_from_data.assert_called()

            self.assertEqual(Match.objects.count(), ROW_COUNT)
            self.assertEqual(TeamMatch.objects.count(), ROW_COUNT * 2)

    @staticmethod
    def __update_or_create_from_data(update_or_create_from_data):
        return update_or_create_from_data
