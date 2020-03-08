"""Django command for seeding the DB with match & prediction data."""

from typing import Tuple, List, cast
from datetime import datetime
from django.utils import timezone
from django.core.management.base import BaseCommand
from django.db import transaction

from server.models import Match, TeamMatch, MLModel, Prediction
from server import data_import
from server.helpers import pivot_team_matches_to_matches
from server.types import MlModel, MatchData

YEAR_RANGE = "2014-2020"
JAN = 1


class Command(BaseCommand):
    """Django class for implementing the DB seeding as a CLI command."""

    help = "Seed the database with team, match, and prediction data."

    def __init__(
        self,
        *args,
        fetch_data=True,
        data_importer=data_import,
        verbose: int = 1,
        **kwargs,
    ) -> None:
        """
        Instantiate the seed_db Command.

        Params:
        fetch_data: Whether to fetch fresh data or load existing data files.
        data_importer: Module for fetching data from external sources.
        verbose: How much information should be printed.
        args: Positional arguments passed directly to the parent BaseCommand.
        Kwargs: Keyword arguments passed directly to the parent BaseCommand.
        """
        super().__init__(*args, **kwargs)

        self.fetch_data = fetch_data
        self.data_importer = data_importer
        self.verbose = verbose
        self.ml_model = None

    def add_arguments(self, parser):
        """
        Accept an ML model name as an argument.

        This allows us to only seed predictions for one model rather than all of them.

        Params:
        -------
        parser: Built-in parser from the Django BaseCommand class.
        """
        parser.add_argument(
            "--ml_model",
            type=str,
            help=(
                "Specify a single MLModel whose associated data "
                "will be added to the DB."
            ),
        )

    def handle(self, *_args, **kwargs) -> None:
        """Seed the DB with all necessary match and prediction data."""
        year_range: str = kwargs.get("year_range") or YEAR_RANGE
        self.verbose = kwargs.get("verbose") or self.verbose
        self.ml_model = kwargs.get("ml_model") or self.ml_model

        if self.verbose == 1:
            ml_model_msg = (
                "" if self.ml_model is None else f" with data for {self.ml_model}"
            )
            print(f"\nSeeding DB{ml_model_msg}...\n")

        years_list = cast(
            Tuple[int, int], tuple([int(year) for year in year_range.split("-")])
        )

        if len(years_list) != 2 or not all(
            [len(str(year)) == 4 for year in years_list]
        ):
            raise ValueError(
                "Years argument must be of form 'yyyy-yyyy' where each 'y' is "
                f"an integer. {year_range} is invalid."
            )

        with transaction.atomic():
            self._create_ml_models()

            # We assume that if we're only adding an MLModel, then we're not doing
            # a full seed
            if self.ml_model is None:
                self._create_matches(years_list)

            self._make_predictions(years_list)

            if self.verbose == 1:
                print("\n...DB seeded!\n")

    def _create_ml_models(self) -> List[MLModel]:
        ml_models = [
            self._build_ml_model(ml_model)
            for ml_model in self.data_importer.fetch_ml_model_info()
            if self.ml_model is None or ml_model["name"] == self.ml_model
        ]

        assert any(ml_models), "Something went wrong and no ML models were saved."

        MLModel.objects.bulk_create(ml_models)

        if self.verbose == 1:
            print("ML models seeded!")

        return ml_models

    def _create_matches(self, years_list: Tuple[int, int]) -> None:
        match_data_frame = self.data_importer.fetch_match_results_data(
            start_date=timezone.make_aware(datetime(years_list[0], 1, 1)),
            end_date=timezone.make_aware(datetime(years_list[1] - 1, 12, 31)),
            fetch_data=self.fetch_data,
        )

        fixture_data = match_data_frame.to_dict("records")

        assert any(fixture_data), "No match data found."

        for fixture_datum in fixture_data:
            self._build_match(fixture_datum)

        if self.verbose == 1:
            print("Match data saved!")

    @staticmethod
    def _build_match(match_data: MatchData) -> None:
        match = Match.get_or_create_from_raw_data(match_data)
        TeamMatch.get_or_create_from_raw_data(match, match_data)

    def _make_predictions(self, year_range: Tuple[int, int]) -> None:
        predictions = self.data_importer.fetch_prediction_data(
            year_range, ml_models=self.ml_model
        )
        home_away_df = pivot_team_matches_to_matches(predictions)

        for pred in home_away_df.to_dict("records"):
            Prediction.update_or_create_from_raw_data(pred)

        if self.verbose == 1:
            print("\nPredictions saved!")

    @staticmethod
    def _build_ml_model(ml_model: MlModel) -> MLModel:
        ml_model_record = MLModel(name=ml_model["name"])
        ml_model_record.full_clean()

        return ml_model_record
