"""Django command for seeding the DB with match & prediction data"""

from datetime import datetime, timezone
from functools import partial
from pydoc import locate
from typing import Tuple, List, Optional, Type
from mypy_extensions import TypedDict
import pandas as pd
import numpy as np
from django.core.management.base import BaseCommand

from server.data_processors import FitzroyDataReader
from server.models import Team, Match, TeamMatch, MLModel, Prediction
from server.ml_models import ml_model
from server.ml_models.betting_model import BettingModel, BettingModelData
from server.ml_models.match_model import MatchModel, MatchModelData
from server.ml_models.all_model import AllModel, AllModelData
from server.ml_models.player_model import PlayerModel, PlayerModelData
from server.ml_models import AvgModel

FixtureData = TypedDict(
    "FixtureData",
    {
        "date": pd.Timestamp,
        "season": int,
        "season_game": int,
        "round": int,
        "home_team": str,
        "away_team": str,
        "venue": str,
    },
)
EstimatorTuple = Tuple[ml_model.MLModel, Type[ml_model.MLModelData]]

PREDICTION_YEARS = "2011-2016"
ESTIMATORS: List[EstimatorTuple] = [
    (BettingModel(name="betting_data"), BettingModelData),
    (MatchModel(name="match_data"), MatchModelData),
    (PlayerModel(name="player_data"), PlayerModelData),
    (AllModel(name="all_data"), AllModelData),
    (AvgModel(name="tipresias"), AllModelData),
]
NO_SCORE = 0
JAN = 1
DEC = 12
RESCUE_LIMIT = datetime(2019, 2, 1)


class Command(BaseCommand):
    help = "Seed the database with team, match, and prediction data."

    def __init__(
        self,
        *args,
        data_reader=FitzroyDataReader(),
        estimators: List[EstimatorTuple] = ESTIMATORS,
        **kwargs,
    ) -> None:
        super().__init__(*args, **kwargs)

        self.data_reader = data_reader
        self.estimators = estimators

    def handle(  # pylint: disable=W0221
        self, *_args, years: str = PREDICTION_YEARS, **_kwargs
    ) -> None:  # pylint: disable=W0613
        print("Seeding DB...\n")

        years_list = [int(year) for year in years.split("-")]

        if len(years_list) != 2 or not all(
            [len(str(year)) == 4 for year in years_list]
        ):
            raise ValueError(
                "Years argument must be of form 'yyyy-yyyy' where each 'y' is an integer. "
                f"{years} is invalid."
            )

        # A little clunky, but mypy complains when you create a tuple with tuple(),
        # which is open-ended, then try to use a restricted tuple type
        prediction_years = (years_list[0], years_list[1])

        yearly_data_frames = [
            self.__fetch_fixture_data(year) for year in range(*prediction_years)
        ]
        fixture_data_frame = pd.concat(
            [data_frame for data_frame in yearly_data_frames if data_frame is not None]
        )

        if not any(fixture_data_frame):
            print("Could not fetch data.\n")
            return None

        if not self.__create_teams(fixture_data_frame):
            return None

        ml_models = self.__create_ml_models()

        if ml_models is None:
            return None

        if not self.__create_matches(fixture_data_frame.to_dict("records")):
            return None

        if self.__make_predictions(prediction_years, ml_models=ml_models):
            print("\n...DB seeded!")
            return None

        return None

    def __fetch_fixture_data(self, year: int) -> Optional[pd.DataFrame]:
        print(f"Fetching fixture for {year}...\n")

        try:
            fixture_data_frame = self.data_reader.get_fixture(season=year)
        # fitzRoy raises RuntimeErrors when you try to fetch too far into the future
        except RuntimeError:
            print(
                f"No data found for {year}. It is likely that the fixture "
                "is not yet available. Please try again later.\n"
            )
            return None
        # TODO: As of 1-1-2019, fitzRoy is returning dodgy fixture data for the 2015
        # season (i.e. NaNs in the date column, and all rounds are 0). This data
        # isn't critical to the core functionality of the app, and I don't know R
        # well enough to debug the package, so I'm just bypassing it for now
        except ValueError:
            if year == 2015 and datetime.now() < RESCUE_LIMIT:
                print(
                    f"There was an error when processing season {year} due to a bug "
                    "in the fitzRoy package. Skipping this season for now.\n"
                )
                return None

            raise

        if not any(fixture_data_frame):
            print(f"No data found for {year}.\n")
            return None

        return fixture_data_frame

    def __create_teams(self, fixture_data: pd.DataFrame) -> bool:
        team_names = np.unique(fixture_data[["home_team", "away_team"]].values)
        teams = [self.__build_team(team_name) for team_name in team_names]

        if not any(teams):
            print("Something went wrong and no teams were saved")
            return False

        Team.objects.bulk_create(teams)
        print("Teams seeded!")
        return True

    def __create_ml_models(self) -> Optional[List[MLModel]]:
        ml_models = [
            self.__build_ml_model(estimator, data_class)
            for estimator, data_class in self.estimators
        ]

        if not any(ml_models):
            print("Something went wrong and no ML models were saved.\n")
            return None

        MLModel.objects.bulk_create(ml_models)
        print("ML models seeded!\n")

        return ml_models

    def __create_matches(self, fixture_data: List[FixtureData]) -> bool:
        if not any(fixture_data):
            print("No match data found.")
            return False

        team_matches = list(
            np.array(
                [self.__build_match(match_data) for match_data in fixture_data]
            ).flatten()
        )

        if not any(team_matches):
            print("Something went wrong, and no team matches were saved.\n")
            return False

        TeamMatch.objects.bulk_create(team_matches)

        print("Match data saved!\n")
        return True

    def __build_match(self, match_data: FixtureData) -> List[TeamMatch]:
        match: Match = Match(
            start_date_time=match_data["date"].to_pydatetime(),
            round_number=int(match_data["round"]),
            venue=match_data["venue"],
        )

        match.full_clean()
        match.save()

        return self.__build_team_match(match, match_data)

    def __make_predictions(
        self,
        prediction_years: Tuple[int, int],
        ml_models: Optional[List[MLModel]] = None,
        round_number: Optional[int] = None,
    ) -> bool:
        make_year_predictions = partial(
            self.__make_year_predictions, ml_models=ml_models, round_number=round_number
        )
        predictions = [make_year_predictions(year) for year in range(*prediction_years)]

        if predictions is None:
            print("Could not find any predictions to save to the DB.\n")
            return False

        Prediction.objects.bulk_create(list(np.array(predictions).flatten()))
        print("Predictions saved!\n")
        return True

    def __make_year_predictions(
        self,
        year: int,
        ml_models: Optional[List[MLModel]] = None,
        round_number: Optional[int] = None,
    ) -> Optional[List[List[Prediction]]]:
        matches_to_predict = Match.objects.filter(
            start_date_time__gt=datetime(year, JAN, 1, tzinfo=timezone.utc),
            start_date_time__lt=datetime(year, DEC, 31, tzinfo=timezone.utc),
        )

        if matches_to_predict is None:
            print("Could not find any matches to make predictions for.\n")
            return None

        ml_models = ml_models or MLModel.objects.all()

        if ml_models is None:
            print("Could not find any ML models in DB to make predictions.\n")
            return None

        # TODO: As of 2-1-2019, fixture round numbers for the 2012 season are incorrect,
        # resulting in various mismatched labels. As with 2015, we're just skipping
        # the season for now while we wait for a fix.
        try:
            make_model_predictions = partial(
                self.__make_model_predictions,
                year,
                matches_to_predict,
                round_number=round_number,
            )
        except KeyError:
            if year == 2012 and datetime.now() < RESCUE_LIMIT:
                print()

            raise

        return [
            make_model_predictions(ml_model_record) for ml_model_record in ml_models
        ]

    def __make_model_predictions(
        self,
        year: int,
        matches: List[Match],
        ml_model_record: MLModel,
        round_number: Optional[int] = None,
    ) -> List[Prediction]:
        estimator = self.__estimator(ml_model_record)
        data_class = locate(ml_model_record.data_class_path)

        data = data_class(train_years=(None, year - 1), test_years=(year, year))
        estimator.fit(*data.train_data())

        X_test, _ = data.test_data()
        y_pred = estimator.predict(X_test)

        data_row_slice = (slice(None), year, slice(round_number, round_number))
        prediction_data = data.data.loc[data_row_slice, :].assign(
            predicted_margin=y_pred
        )

        build_match_prediction = partial(
            self.__build_match_prediction, ml_model_record, prediction_data
        )

        return [build_match_prediction(match) for match in matches]

    @staticmethod
    def __build_ml_model(
        estimator: ml_model.MLModel, data_class: Type[ml_model.MLModelData]
    ) -> MLModel:
        ml_model_record = MLModel(
            name=estimator.name, data_class_path=data_class.class_path()
        )
        ml_model_record.full_clean()

        return ml_model_record

    @staticmethod
    def __build_team(team_name: str) -> Team:
        team = Team(name=team_name)
        team.full_clean()

        return team

    @staticmethod
    def __build_team_match(match: Match, match_data: FixtureData) -> List[TeamMatch]:
        home_team = Team.objects.get(name=match_data["home_team"])
        away_team = Team.objects.get(name=match_data["away_team"])

        home_team_match = TeamMatch(
            team=home_team, match=match, at_home=True, score=NO_SCORE
        )
        away_team_match = TeamMatch(
            team=away_team, match=match, at_home=False, score=NO_SCORE
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

        match_predictions = prediction_data.loc[
            (slice(None), match.year, match.round_number), "predicted_margin"
        ]

        predicted_home_margin = match_predictions.loc[home_team.name].iloc[0]
        predicted_away_margin = match_predictions.loc[away_team.name].iloc[0]

        # predicted_margin is always positive as its always associated with predicted_winner
        predicted_margin = match_predictions.abs().mean()

        if predicted_home_margin > predicted_away_margin:
            predicted_winner = home_team
        else:
            predicted_winner = away_team

        prediction = Prediction(
            match=match,
            ml_model=ml_model_record,
            predicted_margin=round(predicted_margin),
            predicted_winner=predicted_winner,
        )

        prediction.clean_fields()
        prediction.clean()

        return prediction

    @staticmethod
    def __estimator(ml_model_record: MLModel) -> ml_model.MLModel:
        if ml_model_record.name == "betting_data":
            return BettingModel(name=ml_model_record.name)
        if ml_model_record.name == "match_data":
            return MatchModel(name=ml_model_record.name)
        if ml_model_record.name == "player_data":
            return PlayerModel(name=ml_model_record.name)
        if ml_model_record.name == "all_data":
            return AllModel(name=ml_model_record.name)
        if ml_model_record.name == "tipresias":
            return AvgModel(name=ml_model_record.name)

        raise ValueError(f"{ml_model_record.name} is not a recognized ML model name.")
