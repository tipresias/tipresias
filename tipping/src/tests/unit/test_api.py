# pylint: disable=missing-docstring

from unittest import TestCase
from unittest.mock import patch, MagicMock
from datetime import datetime, date
import pytz

import pandas as pd
import numpy as np
from freezegun import freeze_time
from candystore import CandyStore
from faker import Faker

from tests.fixtures import data_factories
from tipping import api
from tipping import models
from tipping.tipping import FootyTipsSubmitter

from tipping.models import Match


TODAY = date.today()
CURRENT_YEAR = TODAY.year
CURRENT_YEAR_RANGE = (CURRENT_YEAR, CURRENT_YEAR + 1)

MATCH_SEASON_RANGE = (2016, 2018)
# We have 2 subtests in 2016 and 1 in 2017, which requires 3 fixture
# and prediction data imports, but only 1 match results data import,
# because it doesn't get called until 2017
MOCK_IMPORT_SEASONS = [min(MATCH_SEASON_RANGE), *range(*MATCH_SEASON_RANGE)]
TIP_SEASON_RANGE = (min(MATCH_SEASON_RANGE), max(MATCH_SEASON_RANGE) + 1)
TIP_DATES = [
    datetime(season, 1, 1, tzinfo=pytz.UTC) for season in range(*TIP_SEASON_RANGE)
]

Fake = Faker()


class TestApi(TestCase):
    def setUp(self):
        candy = CandyStore(seasons=MATCH_SEASON_RANGE)
        fixtures = data_factories.fake_fixture_data(
            fixtures=candy.fixtures(to_dict=None)
        )
        predictions = data_factories.fake_prediction_data(
            fixtures=candy.fixtures(to_dict=None)
        )

        self.fixture_return_values = [
            fixtures.query("year == @season") for season in MOCK_IMPORT_SEASONS
        ]
        self.prediction_return_values = [
            predictions.query("year == @season") for season in MOCK_IMPORT_SEASONS
        ]

        self.mock_submitter = FootyTipsSubmitter()
        self.mock_submitter.submit_tips = MagicMock()

        self.api = api

    @patch("tipping.api.data_export")
    @patch("tipping.api.data_import.DataImporter")
    @patch("tipping.api.settings.Session")
    @patch("tipping.api.models.Match")
    def test_update_fixture_data(
        self, MockMatch, MockSession, MockDataImporter, mock_data_export
    ):
        with freeze_time(datetime(2020, 5, 1, tzinfo=pytz.UTC)):
            right_now = datetime.now(tz=pytz.UTC)
            this_year = right_now.year
            fixture = data_factories.fake_fixture_data(
                seasons=(this_year, this_year + 1)
            )
            upcoming_round = int(
                fixture.query("date > @right_now")["round_number"].min()
            )

            mock_data_import = MagicMock()
            mock_data_import.fetch_fixture_data = MagicMock(return_value=fixture)
            MockDataImporter.return_value = mock_data_import

            mock_data_export.update_fixture_data = MagicMock()

            mock_db_session = MagicMock()
            mock_db_session.add = MagicMock()
            mock_db_session.commit = MagicMock()
            MockSession.return_value = mock_db_session

            fixture_to_update = fixture.query(
                "round_number == @upcoming_round & date > @right_now"
            )
            mock_matches = [
                Match(
                    start_date_time=match["date"],
                    venue=match["venue"],
                    round_number=match["round_number"],
                )
                for _, match in fixture_to_update.iterrows()
            ]
            MockMatch.from_future_fixtures = MagicMock(return_value=mock_matches)

            self.api.update_fixture_data()

            # It posts data to main app
            mock_data_export.update_fixture_data.assert_called()
            call_args = mock_data_export.update_fixture_data.call_args[0]

            data_are_equal = (call_args[0] == fixture_to_update).all().all()
            self.assertTrue(data_are_equal)
            self.assertEqual(call_args[1], upcoming_round)

            # It saves data to DB
            MockMatch.from_future_fixtures.assert_called()
            self.assertEqual(mock_db_session.add.call_count, len(mock_matches))
            mock_db_session.commit.assert_called()

    @patch("tipping.api.settings.Session")
    @patch("tipping.api.data_export")
    @patch("tipping.api.data_import.DataImporter.fetch_match_data")
    def test_update_matches(self, mock_fetch_match_data, mock_data_export, MockSession):
        matches = data_factories.fake_match_data()

        mock_fetch_match_data.return_value = matches
        mock_data_export.update_matches = MagicMock()

        mock_db_session = MagicMock()
        mock_db_session.add = MagicMock()
        mock_db_session.commit = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all = MagicMock(
            return_value=[
                models.Match(
                    start_date_time=data["date"],
                    round_number=data["round_number"],
                    venue=Fake.company(),
                    team_matches=[
                        models.TeamMatch(
                            team=models.Team(name=data["home_team"]), at_home=True
                        ),
                        models.TeamMatch(
                            team=models.Team(name=data["away_team"]), at_home=False
                        ),
                    ],
                )
                for _, data in matches.iterrows()
            ]
        )
        mock_result = MagicMock()
        mock_result.scalars = MagicMock(return_value=mock_scalars)
        mock_db_session.execute = MagicMock(return_value=mock_result)
        MockSession.return_value = mock_db_session

        self.api.update_matches(verbose=0)

        # It posts data to main app
        mock_data_export.update_matches.assert_called()
        call_args = mock_data_export.update_matches.call_args[0]
        data_are_equal = (call_args[0] == matches).all().all()
        self.assertTrue(data_are_equal)

        mock_db_session.commit.assert_called()

    @patch("tipping.api.settings.Session")
    @patch("tipping.api.data_export")
    @patch("tipping.api.data_import.DataImporter")
    def test_update_match_results(
        self, MockDataImporter, mock_data_export, MockSession
    ):
        season = MATCH_SEASON_RANGE[0]
        seasons = (season, season + 1)

        mock_db_session = MagicMock()
        mock_db_session.add = MagicMock()
        mock_db_session.commit = MagicMock()
        mock_db_session.execute = MagicMock()
        MockSession.return_value = mock_db_session
        # We want a date roughly in the middle of the season to make sure
        # we get matches before and after in the fixture
        with freeze_time(datetime(season, 7, 1, tzinfo=pytz.UTC)):
            matches = data_factories.fake_match_data(seasons=seasons)

            right_now = datetime.now(tz=pytz.UTC)  # pylint: disable=unused-variable
            last_match_round_number = matches.query("date < @right_now")[
                "round_number"
            ].max()
            match_results = data_factories.fake_match_results_data(
                matches, round_number=last_match_round_number
            )

            mock_data_import = MagicMock()
            mock_data_import.fetch_fixture_data = MagicMock(return_value=matches)
            mock_data_import.fetch_match_results_data = MagicMock(
                return_value=match_results
            )
            MockDataImporter.return_value = mock_data_import

            mock_data_export.update_match_results = MagicMock()

            mock_scalars = MagicMock()
            mock_scalars.all = MagicMock(
                return_value=[
                    models.Match(
                        start_date_time=data["date"],
                        round_number=data["round_number"],
                        venue=Fake.company(),
                        team_matches=[
                            models.TeamMatch(
                                team=models.Team(name=data["home_team"]), at_home=True
                            ),
                            models.TeamMatch(
                                team=models.Team(name=data["away_team"]), at_home=False
                            ),
                        ],
                    )
                    for _, data in match_results.iterrows()
                ]
            )
            mock_result = MagicMock()
            mock_result.scalars = MagicMock(return_value=mock_scalars)
            mock_db_session.execute = MagicMock(return_value=mock_result)

            self.api.update_match_results(verbose=0)

            # It posts data to main app
            mock_data_export.update_match_results.assert_called()

            # It posts data for the round from the most-recent match
            call_args = mock_data_export.update_match_results.call_args[0]
            data_are_equal = (
                (call_args[0]["round_number"] == last_match_round_number).all().all()
            )
            self.assertTrue(data_are_equal)

            mock_db_session.commit.assert_called()

    @patch("tipping.api.data_export")
    @patch("tipping.api.data_import.DataImporter")
    def test_update_match_predictions(self, MockDataImporter, mock_data_export):
        mock_data_export.update_match_predictions = MagicMock()

        prediction_model_names = (
            pd.concat(self.prediction_return_values)["ml_model"]
            .drop_duplicates()
            .to_numpy()
        )
        prediction_ml_models = data_factories.fake_ml_model_data(
            len(prediction_model_names)
        ).assign(name=prediction_model_names)

        mock_data_import = MagicMock()
        mock_data_import.fetch_ml_model_info = MagicMock(
            return_value=prediction_ml_models
        )
        mock_data_import.fetch_prediction_data = MagicMock(
            side_effect=self.prediction_return_values
        )
        mock_data_import.fetch_fixture_data = MagicMock(
            side_effect=self.fixture_return_values
        )
        MockDataImporter.return_value = mock_data_import

        mock_submitter = FootyTipsSubmitter(verbose=0)
        mock_submitter.submit_tips = MagicMock()

        with self.subTest("with no future match records available"):
            self.api.update_match_predictions(
                tips_submitters=[mock_submitter, mock_submitter], verbose=0
            )

            # It doesn't fetch predictions
            mock_data_import.fetch_prediction_data.assert_not_called()
            # It doesn't send predictions to server API
            mock_data_export.update_match_predictions.assert_not_called()
            # It doesn't try to submit any tips
            mock_submitter.submit_tips.assert_not_called()

        with self.subTest("with at least one future match record"):
            with freeze_time(TIP_DATES[0]):
                self.api.update_match_predictions(
                    tips_submitters=[mock_submitter, mock_submitter], verbose=0
                )

                # It fetches predictions
                mock_data_import.fetch_prediction_data.assert_called()
                # It sends predictions to Tipresias app
                mock_data_export.update_match_predictions.assert_called()
                # It submits tips to all competitions
                self.assertEqual(mock_submitter.submit_tips.call_count, 2)

    @patch("tipping.api.data_import.DataImporter")
    def test_fetch_match_predictions(self, MockDataImporter):
        fixtures = data_factories.fake_fixture_data(seasons=CURRENT_YEAR_RANGE)
        predictions = data_factories.fake_prediction_data(fixtures=fixtures)

        mock_data_import = MagicMock()
        mock_data_import.fetch_prediction_data = MagicMock(return_value=predictions)
        MockDataImporter.return_value = mock_data_import

        round_number = np.random.choice(fixtures["round_number"])
        ml_models = ",".join(set(np.random.choice(predictions["ml_model"], 2)))
        train_models = bool(np.random.randint(0, 2))

        prediction_response = self.api.fetch_match_predictions(
            CURRENT_YEAR_RANGE,
            round_number=round_number,
            ml_models=ml_models,
            train_models=train_models,
        )

        # It calls fetch_prediction_data with the same params
        mock_data_import.fetch_prediction_data.assert_called_with(
            CURRENT_YEAR_RANGE,
            round_number=round_number,
            ml_model_names=ml_models,
            train_models=train_models,
        )
        # It returns predictions organised by match
        self.assertEqual(
            {
                "home_team",
                "year",
                "round_number",
                "away_team",
                "ml_model",
                "home_predicted_margin",
                "away_predicted_margin",
                "home_predicted_win_probability",
                "away_predicted_win_probability",
            },
            set(prediction_response.columns),
        )
        self.assertEqual(len(fixtures), len(prediction_response))

    @patch("tipping.api.data_import.DataImporter")
    def test_fetch_matches(self, MockDataImporter):
        matches = data_factories.fake_match_data()

        mock_data_import = MagicMock()
        mock_data_import.fetch_match_data = MagicMock(return_value=matches)
        MockDataImporter.return_value = mock_data_import

        match_dates = np.random.choice(matches["date"], size=2)
        fetch_data = bool(np.random.randint(0, 2))

        match_response = self.api.fetch_matches(
            start_date=min(match_dates),
            end_date=max(match_dates),
            fetch_data=fetch_data,
        )

        # It calls fetch_match_data with the same params
        mock_data_import.fetch_match_data.assert_called_with(
            min(match_dates),
            max(match_dates),
            fetch_data=fetch_data,
        )

        match_columns = set(match_response.columns)
        required_columns = {
            "date",
            "year",
            "round",
            "round_number",
            "home_team",
            "away_team",
            "venue",
            "home_score",
            "away_score",
        }
        # It returns match data
        self.assertEqual(
            match_columns & required_columns,
            required_columns,
        )
        self.assertEqual(len(matches), len(match_response))

    @patch("tipping.api.data_import.DataImporter")
    def test_fetch_ml_models(self, MockDataImporter):
        N_ML_MODELS = 2
        ml_models = data_factories.fake_ml_model_data(N_ML_MODELS)

        mock_data_import = MagicMock()
        mock_data_import.fetch_ml_model_info = MagicMock(return_value=ml_models)
        MockDataImporter.return_value = mock_data_import

        ml_model_response = self.api.fetch_ml_models()

        # It calls fetch_ml_model_info
        mock_data_import.fetch_ml_model_info.assert_called()
        # It returns ML model data
        self.assertEqual(
            {"name", "prediction_type", "trained_to", "data_set", "label_col"},
            set(ml_model_response.columns),
        )
        self.assertEqual(N_ML_MODELS, len(ml_model_response))
