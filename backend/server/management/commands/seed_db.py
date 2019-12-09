"""Django command for seeding the DB with match & prediction data"""

from typing import Tuple, List
from datetime import datetime
import pandas as pd
import numpy as np
from django.utils import timezone
from django.core.management.base import BaseCommand

from server.models import Team, Match, TeamMatch, MLModel, Prediction
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

        # A little clunky, but mypy complains when you create a tuple with tuple(),
        # which is open-ended, then try to use a restricted tuple type
        year_range_tuple = (years_list[0], years_list[1])

        match_data_frame = self.data_importer.fetch_match_results_data(
            start_date=timezone.make_aware(datetime(years_list[0], 1, 1)),
            end_date=timezone.make_aware(datetime(years_list[1] - 1, 12, 31)),
            fetch_data=self.fetch_data,
        )

        # Putting saving records in a try block, so we can go back and delete everything
        # if an error is raised
        try:
            self.__create_teams(match_data_frame)
            self.__create_ml_models()
            self.__create_matches(match_data_frame.to_dict("records"))
            self.__make_predictions(year_range_tuple)

            if self.verbose == 1:
                print("\n...DB seeded!\n")
        except:
            if self.verbose == 1:
                print("\nRolling back DB changes...")

            Team.objects.all().delete()
            MLModel.objects.all().delete()
            Match.objects.all().delete()

            if self.verbose == 1:
                print("...DB unseeded!\n")

            raise

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

        build_matches = (
            self.__build_match(fixture_datum) for fixture_datum in fixture_data
        )
        list(build_matches)

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

    @staticmethod
    def __build_match_prediction(
        ml_model_record: MLModel, prediction_data: pd.DataFrame, match: Match
    ) -> Prediction:
        home_team = match.teammatch_set.get(at_home=True).team
        away_team = match.teammatch_set.get(at_home=False).team

        match_prediction = prediction_data.loc[
            ([home_team.name, away_team.name], match.year, match.round_number),
            "predicted_margin",
        ]

        predicted_home_margin = match_prediction.loc[home_team.name].iloc[0]
        predicted_away_margin = match_prediction.loc[away_team.name].iloc[0]

        # predicted_margin is always positive as its always associated with predicted_winner
        predicted_margin = match_prediction.abs().mean()

        if predicted_home_margin > predicted_away_margin:
            predicted_winner = home_team
        elif predicted_away_margin > predicted_home_margin:
            predicted_winner = away_team
        else:
            raise ValueError(
                "Predicted home and away margins are equal, which is basically impossible, "
                "so figure out what's going on:\n"
                f"home_team = {home_team.name}\n"
                f"away_team = {away_team.name}\n"
                "data ="
                f"{match_prediction}"
            )

        prediction = Prediction(
            match=match,
            ml_model=ml_model_record,
            predicted_margin=predicted_margin,
            predicted_winner=predicted_winner,
        )

        prediction.clean_fields()
        prediction.clean()

        return prediction
