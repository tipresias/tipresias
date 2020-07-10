"""Django command for seeding the DB with match & prediction data."""

from typing import Tuple, List, cast, Optional, Dict, Any, Union
from urllib.parse import urljoin

from django.core.management.base import BaseCommand
from django.db import transaction
from django.conf import settings
import requests

from server.models import Match, TeamMatch, MLModel, Prediction
from server.types import MatchData, MLModelInfo, CleanPredictionData

YEAR_RANGE = "2014-2020"


class DataImporter:
    """Imports data from the tipping service."""

    def fetch_ml_models(self) -> List[MLModel]:
        """
        Fetch general info about all saved ML models.

        Returns:
        --------
        A list of objects with basic info about each ML model.
        """
        return cast(List[MLModel], self._fetch_data("ml_models"))

    def fetch_match_results(
        self, start_date: str, end_date: str, fetch_data: bool = False
    ) -> List[MatchData]:
        """
        Fetch results data for past matches.

        Params:
        -------
        start_date: Date-time string that determines the earliest date
            for which to fetch data. Format is 'yyyy-mm-dd'.
        end_date: Date-time string that determines the latest date
            for which to fetch data. Format is 'yyyy-mm-dd'.
        fetch_data: Whether to fetch fresh data. Non-fresh data goes up to end
            of previous season.

        Returns:
        --------
            List of match results data dicts.
        """
        return cast(
            List[MatchData],
            self._fetch_data(
                "matches",
                {
                    "start_date": start_date,
                    "end_date": end_date,
                    "fetch_data": fetch_data,
                },
            ),
        )

    def fetch_match_predictions(
        self,
        year_range: str,
        round_number: Optional[int] = None,
        ml_models: Optional[List[str]] = None,
        train_models: Optional[bool] = False,
    ) -> List[CleanPredictionData]:
        """
        Fetch prediction data from ML models.

        Params:
        -------
        year_range: Min (inclusive) and max (exclusive) years for which to fetch data.
            Format is 'yyyy-yyyy'.
        round_number: Specify a particular round for which to fetch data.
        ml_models: List of ML model names to use for making predictions.
        train_models: Whether to train models in between predictions (only applies
            when predicting across multiple seasons).

        Returns:
        --------
            List of prediction data dictionaries.
        """
        return cast(
            List[CleanPredictionData],
            self._fetch_data(
                "predictions",
                {
                    "year_range": year_range,
                    "round_number": round_number,
                    "ml_models": ml_models,
                    "train_models": train_models,
                },
            ),
        )

    @staticmethod
    def _fetch_data(
        path: str, params: Optional[Dict[str, Any]] = None
    ) -> List[Union[MLModelInfo, MatchData, CleanPredictionData]]:
        params = params or {}

        headers = {"Authorization": f"Bearer {settings.TIPPING_SERVICE_TOKEN}"}

        service_url = urljoin(settings.TIPPING_SERVICE, path)
        clean_params = {
            key: str(value) for key, value in params.items() if value is not None
        }

        response = requests.get(service_url, params=clean_params, headers=headers)

        if 200 <= response.status_code < 300:
            return response.json().get("data")

        raise Exception(
            f"Bad response from application when requesting {service_url}:\n"
            f"Status: {response.status_code}\n"
            f"Headers: {response.headers}\n"
            f"Body: {response.text}"
        )


class Command(BaseCommand):
    """Django class for implementing the DB seeding as a CLI command."""

    help = "Seed the database with team, match, and prediction data."

    def __init__(
        self,
        *args,
        fetch_data=True,
        data_importer=DataImporter(),
        verbose: int = 1,
        **kwargs,
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
            start_date=f"{self._year_range[0]}-01-01",
            end_date=f"{self._year_range[1] - 1}-12-31",
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
