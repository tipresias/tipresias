"""Django command for seeding the DB with match & prediction data"""

from typing import Tuple, List, cast
from datetime import datetime
from django.utils import timezone
from django.core.management.base import BaseCommand
from django.db import transaction

from server.models import Match, TeamMatch, MLModel, Prediction
from server import data_import
from server.helpers import pivot_team_matches_to_matches
from server.types import MlModel, MatchData

YEAR_RANGE = "2014-2019"
JAN = 1


class Command(BaseCommand):
    help = "Seed the database with team, match, and prediction data."

    def __init__(
        self, *args, fetch_data=True, data_importer=data_import, **kwargs
    ) -> None:
        super().__init__(*args, **kwargs)

        self.fetch_data = fetch_data
        self.data_importer = data_importer

    def handle(  # pylint: disable=W0221
        self, *_args, year_range: str = YEAR_RANGE, verbose: int = 1, **_kwargs
    ) -> None:  # pylint: disable=W0613
        self.verbose = verbose  # pylint: disable=W0201

        if self.verbose == 1:
            print("\nSeeding DB...\n")

        years_list = [int(year) for year in year_range.split("-")]

        if len(years_list) != 2 or not all(
            [len(str(year)) == 4 for year in years_list]
        ):
            raise ValueError(
                "Years argument must be of form 'yyyy-yyyy' where each 'y' is "
                f"an integer. {year_range} is invalid."
            )

        match_data_frame = self.data_importer.fetch_match_results_data(
            start_date=timezone.make_aware(datetime(years_list[0], 1, 1)),
            end_date=timezone.make_aware(datetime(years_list[1] - 1, 12, 31)),
            fetch_data=self.fetch_data,
        )

        with transaction.atomic():
            self.__create_ml_models()
            self.__create_matches(match_data_frame.to_dict("records"))
            self.__make_predictions(cast(Tuple[int, int], years_list))

            if self.verbose == 1:
                print("\n...DB seeded!\n")

    def __create_ml_models(self) -> List[MLModel]:
        ml_models = [
            self.__build_ml_model(ml_model)
            for ml_model in self.data_importer.fetch_ml_model_info()
        ]

        if not any(ml_models):
            raise ValueError("Something went wrong and no ML models were saved.")

        MLModel.objects.bulk_create(ml_models)

        if self.verbose == 1:
            print("ML models seeded!")

        return ml_models

    def __create_matches(self, fixture_data: List[MatchData]) -> None:
        if not any(fixture_data):
            raise ValueError("No match data found.")

        for fixture_datum in fixture_data:
            self.__build_match(fixture_datum)

        if self.verbose == 1:
            print("Match data saved!")

    @staticmethod
    def __build_match(match_data: MatchData) -> None:
        match = Match.get_or_create_from_raw_data(match_data)
        TeamMatch.get_or_create_from_raw_data(match, match_data)

    def __make_predictions(self, year_range: Tuple[int, int]) -> None:
        predictions = self.data_importer.fetch_prediction_data(
            year_range, verbose=self.verbose
        )
        home_away_df = pivot_team_matches_to_matches(predictions)

        for pred in home_away_df.to_dict("records"):
            Prediction.update_or_create_from_raw_data(pred)

        if self.verbose == 1:
            print("\nPredictions saved!")

    @staticmethod
    def __build_ml_model(ml_model: MlModel) -> MLModel:
        ml_model_record = MLModel(name=ml_model["name"], filepath=ml_model["filepath"])
        ml_model_record.full_clean()

        return ml_model_record
