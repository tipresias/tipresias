"""Django command for seeding the DB with match & prediction data"""

import itertools
from functools import partial
from typing import Tuple, List, Optional, Union
from datetime import datetime
from mypy_extensions import TypedDict
import pandas as pd
import numpy as np
from django import utils
from django.core.management.base import BaseCommand

from server.models import Team, Match, TeamMatch, MLModel, Prediction
from machine_learning.data_import import FitzroyDataImporter
from machine_learning.ml_estimators import BaseMLEstimator
from machine_learning.ml_data import BaseMLData, JoinedMLData
from machine_learning.ml_estimators import BenchmarkEstimator, BaggingEstimator

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
        data=JoinedMLData(fetch_data=True),
        **kwargs,
    ) -> None:
        super().__init__(*args, **kwargs)

        self.data_reader = data_reader
        self.estimators = estimators
        self.data = data

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
        )

        # Putting saving records in a try block, so we can go back and delete everything
        # if an error is raised
        try:
            self.__create_teams(match_data_frame)
            ml_models = self.__create_ml_models()
            self.__create_matches(match_data_frame.to_dict("records"))
            self.__make_predictions(year_range_tuple, ml_models=ml_models)

            if self.verbose == 1:
                print("\n...DB seeded!\n")
        except:
            print("\nRolling back DB changes...")
            Team.objects.all().delete()
            MLModel.objects.all().delete()
            Match.objects.all().delete()
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

    def __make_predictions(
        self,
        year_range: Tuple[int, int],
        ml_models: Optional[List[MLModel]] = None,
        round_number: Optional[int] = None,
    ) -> None:
        ml_models = ml_models or MLModel.objects.all()

        if ml_models is None or not any(ml_models):
            if self.verbose == 1:
                raise ValueError(
                    "\tCould not find any ML models in DB to make predictions."
                )

        # Loading the data here, because it makes for a weird set of messages to do it
        # in the middle of loading models & making predictions
        self.data.data  # pylint: disable=W0104

        make_model_predictions = partial(
            self.__make_model_predictions, year_range, round_number=round_number
        )
        model_predictions_list = [
            make_model_predictions(ml_model_record) for ml_model_record in ml_models
        ]
        model_predictions = list(itertools.chain.from_iterable(model_predictions_list))

        if not any(model_predictions):
            raise ValueError("Could not find any predictions to save to the DB.")

        Prediction.objects.bulk_create(model_predictions)

        if self.verbose == 1:
            print("\nPredictions saved!")

    def __make_model_predictions(
        self,
        year_range: Tuple[int, int],
        ml_model_record: MLModel,
        round_number: Optional[int] = None,
    ) -> List[Prediction]:
        if self.verbose == 1:
            print(f"\nMaking predictions with {ml_model_record.name}...")

        estimator = ml_model_record.load_estimator()

        make_year_predictions = partial(
            self.__make_year_predictions,
            ml_model_record,
            estimator,
            round_number=round_number,
        )

        year_prediction_lists = [
            make_year_predictions(year) for year in range(*year_range)
        ]

        return list(itertools.chain.from_iterable(year_prediction_lists))

    # TODO: Got the following error when trying to implement multiprocessing:
    # TypeError: cannot serialize '_io.TextIOWrapper' object
    # Not too sure on the cause, but it works okay for now (it's just slow).
    def __make_year_predictions(
        self,
        ml_model_record: MLModel,
        estimator: BaseMLEstimator,
        year: int,
        round_number: Optional[int] = None,
    ) -> List[Prediction]:
        if self.verbose == 1:
            print(f"\tMaking predictions for {year}...")

        matches_to_predict = Match.objects.filter(start_date_time__year=year)

        if matches_to_predict is None or not any(matches_to_predict):
            if self.verbose == 1:
                print(
                    f"\tCould not find any matches from season {year} to make predictions for."
                )

            return []

        self.data.train_years = (None, year - 1)
        self.data.test_years = (year, year)
        data_row_slice = (slice(None), year, slice(round_number, round_number))
        prediction_data = self.__predict(estimator, self.data, data_row_slice)

        if prediction_data is None:
            return []

        build_match_prediction = partial(
            self.__build_match_prediction, ml_model_record, prediction_data
        )

        return [build_match_prediction(match) for match in matches_to_predict]

    def __predict(
        self,
        estimator: BaseMLEstimator,
        data: BaseMLData,
        data_row_slice: Tuple[slice, int, slice],
    ) -> Optional[pd.DataFrame]:
        X_train, y_train = data.train_data()
        X_test, _ = data.test_data()

        # On the off chance that we try to run predictions for years that have no relevant
        # prediction data
        if X_train.empty or y_train.empty or X_test.empty:
            if self.verbose == 1:
                print(
                    "Some required data was missing for predicting for season "
                    f"{data.test_years[0]}.\n"
                    f"{'X_train is empty' if X_train.empty else ''}"
                    f"{', y_train is empty' if y_train.empty else ''}"
                    f"{', and y_test is empty.' if X_train.empty else ''}"
                )

            return None

        estimator.fit(X_train, y_train)

        y_pred = estimator.predict(X_test)

        return data.data.loc[data_row_slice, :].assign(predicted_margin=y_pred)

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
