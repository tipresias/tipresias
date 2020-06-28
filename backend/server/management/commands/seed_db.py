"""Django command for seeding the DB with match & prediction data."""

from typing import Tuple, List, cast, Optional
from datetime import datetime
from django.utils import timezone
from django.core.management.base import BaseCommand
from django.db import transaction

from data import api
from server.models import Match, TeamMatch, MLModel, Prediction
from server.types import MatchData, MLModelInfo

YEAR_RANGE = "2014-2020"
JAN = 1


class Command(BaseCommand):
    """Django class for implementing the DB seeding as a CLI command."""

    help = "Seed the database with team, match, and prediction data."

    def __init__(
        self, *args, fetch_data=True, data_importer=api, verbose: int = 1, **kwargs,
    ) -> None:
        """
        Instantiate the seed_db Command.

        Params:
        -------
        fetch_data: Whether to fetch fresh data or load existing data files.
        data_importer: Module for fetching data from external sources.
        verbose: How much information should be printed.
        year_range:
        args: Positional arguments passed directly to the parent BaseCommand.
        kwargs: Keyword arguments passed directly to the parent BaseCommand.
        """
        super().__init__(*args, **kwargs)

        self.fetch_data = fetch_data
        self.data_importer = data_importer
        self.verbose: int = verbose
        self.ml_model: Optional[str] = None
        self.year_range: str = YEAR_RANGE

    def add_arguments(self, parser):
        """
        Add arguments to the seed_db django command.

        Adds the following arguments:
        --ml_model: Name of an MLModel. This will be the only model whose predictions
            are seeded.
        --year_range: Year range of form yyyy-yyyy. These will be the only seasons
            for which predictions are seeded. Final year in range is excluded
            per Python's `range` function.

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

        parser.add_argument(
            "--year_range",
            type=str,
            help=(
                "Specify a range of seasons (inclusive start, exclusive end, "
                "per Python's `range`) for which data will be added to the DB. "
                "Format is yyyy-yyyy."
            ),
        )

    def handle(self, *_args, **kwargs) -> None:
        """
        Seed the DB with all necessary match and prediction data.

        Params:
        -------
        ml_model: Name of the model to use for generating prediction data.
            Uses all available ml_models if omitted.
        year_range: Range of years for which to generate data. Uses `2014-2020`
            if omitted.
        """
        self.year_range = kwargs.get("year_range") or self.year_range
        self.verbose = kwargs.get("verbose") or self.verbose
        self.ml_model = kwargs.get("ml_model") or self.ml_model

        if self.verbose == 1:
            ml_model_msg = (
                "" if self.ml_model is None else f" with data for {self.ml_model}"
            )
            print(f"\nSeeding DB{ml_model_msg}...\n")

        with transaction.atomic():
            self._create_ml_models()

            # We assume that if we're only adding an MLModel, then we're not doing
            # a full seed
            if self.ml_model is None:
                self._create_matches()

            self._make_predictions()

            if self.verbose == 1:
                print("\n...DB seeded!\n")

    def _create_ml_models(self) -> List[MLModel]:
        ml_models = [
            self._get_or_create_ml_model(ml_model)
            for ml_model in self.data_importer.fetch_ml_models()
            if self.ml_model is None or ml_model["name"] == self.ml_model
        ]

        assert any(ml_models), "Something went wrong and no ML models were saved."

        if self.verbose == 1:
            print("ML models seeded!")

        return ml_models

    def _create_matches(self) -> None:
        match_data = self.data_importer.fetch_match_results(
            start_date=timezone.make_aware(datetime(self._year_range[0], 1, 1)),
            end_date=timezone.make_aware(datetime(self._year_range[1] - 1, 12, 31)),
            fetch_data=self.fetch_data,
        )

        assert any(match_data), "No match data found."

        for match_datum in match_data:
            self._get_or_create_match(match_datum)

        if self.verbose == 1:
            print("Match data saved!")

    @staticmethod
    def _get_or_create_match(match_data: MatchData) -> None:
        match = Match.get_or_create_from_raw_data(match_data)
        TeamMatch.get_or_create_from_raw_data(match, match_data)

    def _make_predictions(self) -> None:
        predictions = self.data_importer.fetch_match_predictions(
            self._year_range, ml_models=[self.ml_model], train_models=True
        )

        for pred in predictions:
            Prediction.update_or_create_from_raw_data(pred)

        if self.verbose == 1:
            print("\nPredictions saved!")

    @staticmethod
    def _get_or_create_ml_model(ml_model: MLModelInfo) -> MLModel:
        ml_model_record, _created = MLModel.objects.get_or_create(name=ml_model["name"])
        ml_model_record.full_clean()

        return ml_model_record

    @property
    def _year_range(self) -> Tuple[int, int]:
        year_range_limits = self.year_range.split("-")

        assert len(year_range_limits) == 2 and all(
            [len(year) == 4 for year in year_range_limits]
        ), (
            "Years argument must be of form 'yyyy-yyyy' where each 'y' is an integer. "
            f"{self.year_range} is invalid."
        )

        year_ints = cast(
            Tuple[int, int], tuple([int(year) for year in year_range_limits])
        )

        return year_ints
