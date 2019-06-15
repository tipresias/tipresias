"""Django command for seeding the DB with match & prediction data"""

import itertools
from typing import Tuple, List, Union
from datetime import datetime
from mypy_extensions import TypedDict
import pandas as pd
import numpy as np
from django import utils
from django.core.management.base import BaseCommand

from server.models import Team, Match, TeamMatch, MLModel, Prediction
from server import data_import
from machine_learning.data_import import FitzroyDataImporter
from machine_learning.ml_estimators import BaseMLEstimator
from machine_learning.ml_estimators import BenchmarkEstimator, BaggingEstimator
from machine_learning.data_transformation.data_cleaning import clean_match_data

MatchData = TypedDict(
    "MatchData",
    {
        "date": Union[datetime, pd.Timestamp],
        "season": int,
        "round_number": int,
        "round": str,
        "crowd": int,
        "home_team": str,
        "away_team": str,
        "home_score": int,
        "away_score": int,
        "venue": str,
    },
)

YEAR_RANGE = "2014-2019"
ESTIMATORS: List[BaseMLEstimator] = [
    BenchmarkEstimator(name="benchmark_estimator"),
    BaggingEstimator(name="tipresias"),
]
NO_SCORE = 0
JAN = 1


class Command(BaseCommand):
    help = "Seed the database with team, match, and prediction data."

    def __init__(
        self,
        *args,
        data_reader=FitzroyDataImporter(),
        estimators: List[BaseMLEstimator] = ESTIMATORS,
        prediction_data=data_import,
        **kwargs,
    ) -> None:
        super().__init__(*args, **kwargs)

        self.data_reader = data_reader
        self.estimators = estimators
        self.prediction_data = prediction_data

    def handle(  # pylint: disable=W0221
        self, *_args, year_range: str = YEAR_RANGE, verbose: int = 1, **_kwargs
    ) -> None:  # pylint: disable=W0613
        self.verbose = verbose  # pylint: disable=W0201
        self.data_reader.verbose = verbose

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

        match_data_frame = self.data_reader.match_results(
            start_date=f"{years_list[0]}-01-01", end_date=f"{years_list[1] - 1}-12-31"
        ).pipe(clean_match_data)

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

    def __create_teams(self, fixture_data: pd.DataFrame) -> None:
        team_names = np.unique(fixture_data[["home_team", "away_team"]].values)
        teams = [self.__build_team(team_name) for team_name in team_names]

        if not any(teams):
            raise ValueError("Something went wrong and no teams were saved.")

        Team.objects.bulk_create(teams)

        if self.verbose == 1:
            print("Teams seeded!")

    def __create_ml_models(self) -> List[MLModel]:
        ml_models = [self.__build_ml_model(estimator) for estimator in self.estimators]

        if not any(ml_models):
            raise ValueError("Something went wrong and no ML models were saved.")

        MLModel.objects.bulk_create(ml_models)

        if self.verbose == 1:
            print("ML models seeded!")

        return ml_models

    def __create_matches(self, fixture_data: List[MatchData]) -> None:
        if not any(fixture_data):
            raise ValueError("No match data found.")

        team_matches = [self.__build_match(match_data) for match_data in fixture_data]
        team_matches_to_save = list(itertools.chain.from_iterable(team_matches))

        if not any(team_matches):
            raise ValueError("Something went wrong, and no team matches were saved.")

        TeamMatch.objects.bulk_create(team_matches_to_save)

        if self.verbose == 1:
            print("Match data saved!")

    def __build_match(self, match_data: MatchData) -> List[TeamMatch]:
        raw_date = match_data["date"]
        python_date = (
            raw_date if isinstance(raw_date, datetime) else raw_date.to_pydatetime()
        )

        # 'make_aware' raises error if datetime already has a timezone
        if (
            python_date.tzinfo is None
            or python_date.tzinfo.utcoffset(python_date) is None
        ):
            match_date = utils.timezone.make_aware(python_date)
        else:
            match_date = python_date

        match: Match = Match(
            start_date_time=match_date,
            round_number=int(match_data["round_number"]),
            venue=match_data["venue"],
        )

        match.full_clean()
        match.save()

        return self.__build_team_match(match, match_data)

    def __make_predictions(self, year_range: Tuple[int, int]) -> None:
        predictions = self.prediction_data.fetch_prediction_data(
            year_range, verbose=self.verbose
        )

        predictions_df = pd.DataFrame(predictions)

        home_df = (
            predictions_df.query("at_home == 1")
            .rename(
                columns={
                    "team": "home_team",
                    "oppo_team": "away_team",
                    "predicted_margin": "home_margin",
                }
            )
            .drop("at_home", axis=1)
        )
        away_df = (
            predictions_df.query("at_home == 0")
            .rename(
                columns={
                    "team": "away_team",
                    "oppo_team": "home_team",
                    "predicted_margin": "away_margin",
                }
            )
            .drop("at_home", axis=1)
        )

        home_away_df = home_df.merge(
            away_df,
            on=["home_team", "away_team", "year", "round_number", "ml_model"],
            how="inner",
        )

        for pred in home_away_df.to_dict("records"):
            Prediction.update_or_create_from_data(pred)

        if self.verbose == 1:
            print("\nPredictions saved!")

    @staticmethod
    def __build_ml_model(estimator: BaseMLEstimator) -> MLModel:
        ml_model_record = MLModel(
            name=estimator.name, filepath=estimator.pickle_filepath()
        )
        ml_model_record.full_clean()

        return ml_model_record

    @staticmethod
    def __build_team(team_name: str) -> Team:
        team = Team(name=team_name)
        team.full_clean()

        return team

    @staticmethod
    def __build_team_match(match: Match, match_data: MatchData) -> List[TeamMatch]:
        home_team = Team.objects.get(name=match_data["home_team"])
        away_team = Team.objects.get(name=match_data["away_team"])

        home_team_match = TeamMatch(
            team=home_team, match=match, at_home=True, score=match_data["home_score"]
        )
        away_team_match = TeamMatch(
            team=away_team, match=match, at_home=False, score=match_data["away_score"]
        )

        home_team_match.clean_fields()
        home_team_match.clean()
        away_team_match.clean_fields()
        away_team_match.clean()

        return [home_team_match, away_team_match]

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
