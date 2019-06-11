"""Module for 'tip' command that updates predictions for upcoming AFL matches"""

import os
from functools import partial, reduce
from datetime import datetime, date
from typing import List, Optional
from django.core.management.base import BaseCommand
from django import utils
import pandas as pd
import numpy as np
from sklearn.externals import joblib

from project.settings.common import BASE_DIR, MELBOURNE_TIMEZONE
from server.models import Match, TeamMatch, Team, MLModel, Prediction
from server.types import CleanedFixtureData, PredictionData
from server import data_import
from machine_learning.data_import import FitzroyDataImporter
from machine_learning.ml_data import JoinedMLData
from machine_learning.data_transformation.data_cleaning import clean_fixture_data


NO_SCORE = 0
# We calculate rolling sums/means for some features that can span over 5 seasons
# of data, so we're setting it to 10 to be on the safe side.
N_SEASONS_FOR_PREDICTION = 10
# We want to limit the amount of data loaded as much as possible,
# because we only need the full data set for model training and data analysis,
# and we want to limit memory usage and speed up data processing for tipping
PREDICTION_DATA_START_DATE = f"{date.today().year - N_SEASONS_FOR_PREDICTION}-01-01"


class Command(BaseCommand):
    """manage.py command for 'tip' that updates predictions for upcoming AFL matches"""

    help = """
    Check if there are upcoming AFL matches and make predictions on results
    for all unplayed matches in the upcoming/current round.
    """

    def __init__(
        self,
        *args,
        data_reader=FitzroyDataImporter(),
        fetch_data=True,
        data=JoinedMLData(fetch_data=True, start_date=PREDICTION_DATA_START_DATE),
        **kwargs,
    ) -> None:
        super().__init__(*args, **kwargs)

        self.data_reader = data_reader
        self.right_now = datetime.now(tz=MELBOURNE_TIMEZONE)
        self.current_year = self.right_now.year
        self.fetch_data = fetch_data
        self.data = data

    def handle(self, *_args, verbose=1, **_kwargs) -> None:  # pylint: disable=W0221
        """Run 'tip' command"""

        self.verbose = verbose  # pylint: disable=W0201
        self.data_reader.verbose = verbose

        fixture_data_frame = self.__fetch_fixture_data(self.current_year).pipe(
            clean_fixture_data
        )
        upcoming_round = fixture_data_frame["round_number"].min()

        if fixture_data_frame is None:
            raise ValueError("Could not fetch data.")

        saved_match_count = Match.objects.filter(
            start_date_time__gt=self.right_now
        ).count()

        if saved_match_count == 0:
            if self.verbose == 1:
                print(
                    f"No existing match records found for round {upcoming_round}. "
                    "Creating new match and prediction records...\n"
                )

            if self.verbose == 1:
                print(
                    f"Saving Match and TeamMatch records for round {upcoming_round}..."
                )

            self.__create_matches(fixture_data_frame.to_dict("records"))
        else:
            if self.verbose == 1:
                print(
                    f"{saved_match_count} unplayed match records found for round {upcoming_round}. "
                    "Updating associated prediction records with new model predictions.\n"
                )

        upcoming_round_year = fixture_data_frame["date"].map(lambda x: x.year).max()

        if self.verbose == 1:
            print("Saving prediction records...")

        self.__make_predictions(upcoming_round_year, upcoming_round)

        return None

    def __fetch_fixture_data(self, year: int) -> pd.DataFrame:
        if self.verbose == 1:
            print(f"Fetching fixture for {year}...\n")

        fixture_data_frame = self.data_reader.fetch_fixtures(
            start_date=f"{year}-01-01", end_date=f"{year}-12-31"
        )

        latest_match = fixture_data_frame["date"].max()

        if self.right_now > latest_match:
            print(
                f"No unplayed matches found in {year}. We will try to fetch "
                f"fixture for {year + 1}.\n"
            )

            fixture_data_frame = self.data_reader.fetch_fixtures(
                start_date=f"{year}-01-01", end_date=f"{year}-12-31"
            )

            latest_match = fixture_data_frame["date"].max()

            if self.right_now > latest_match:
                raise ValueError(
                    f"No unplayed matches found in {year + 1}, and we're not going "
                    "to keep trying. Please try a season that hasn't been completed.\n"
                )

        return fixture_data_frame

    def __create_matches(self, fixture_data: List[CleanedFixtureData]) -> None:
        if not any(fixture_data):
            raise ValueError("No fixture data found.")

        round_number = {match_data["round_number"] for match_data in fixture_data}.pop()
        year = {match_data["year"] for match_data in fixture_data}.pop()

        team_match_lists = [
            self.__build_match(match_data) for match_data in fixture_data
        ]

        compacted_team_match_lists = [
            team_match_list
            for team_match_list in team_match_lists
            if team_match_list is not None
        ]

        team_matches_to_save: List[TeamMatch] = reduce(
            lambda acc_list, curr_list: acc_list + curr_list,
            compacted_team_match_lists,
            [],
        )

        team_match_count = TeamMatch.objects.filter(
            match__start_date_time__year=year, match__round_number=round_number
        ).count()

        if not any(team_matches_to_save) and team_match_count == 0:
            raise ValueError("Something went wrong, and no team matches were saved.\n")

        TeamMatch.objects.bulk_create(team_matches_to_save)

        if self.verbose == 1:
            print("Match data saved!\n")

    def __build_match(
        self, match_data: CleanedFixtureData
    ) -> Optional[List[TeamMatch]]:
        raw_date = (
            match_data["date"].to_pydatetime()
            if isinstance(match_data["date"], pd.Timestamp)
            else match_data["date"]
        )

        # 'make_aware' raises error if datetime already has a timezone
        if raw_date.tzinfo is None or raw_date.tzinfo.utcoffset(raw_date) is None:
            match_date = utils.timezone.make_aware(
                raw_date, timezone=MELBOURNE_TIMEZONE
            )
        else:
            match_date = raw_date

        match, was_created = Match.objects.get_or_create(
            start_date_time=match_date,
            round_number=int(match_data["round_number"]),
            venue=match_data["venue"],
        )

        if was_created:
            match.full_clean()

        return self.__build_team_match(match, match_data)

    def __make_predictions(self, year: int, round_number: int) -> None:
        predictions = data_import.fetch_predictions(year, round_number)
        predictions_df = pd.DataFrame(predictions)

        home_df = (
            predictions_df.query("at_home == 1")
            .rename(
                columns={
                    "team": "home_team",
                    "oppo_team": "away_team",
                    "margin": "home_margin",
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
                    "margin": "away_margin",
                }
            )
            .drop("at_home", axis=1)
        )

        home_away_df = home_df.merge(
            away_df,
            on=["home_team", "away_team", "year", "round_number", "ml_model"],
            how="inner",
        )

        predictions_to_save = [
            self.__build_match_prediction(pred)
            for pred in home_away_df.to_dict("records")
        ]

        Prediction.objects.bulk_create(predictions_to_save)

        if self.verbose == 1:
            print("Predictions saved!\n")

    @staticmethod
    def __build_match_prediction(prediction_data: PredictionData) -> List[Prediction]:
        home_team = prediction_data["home_team"]
        away_team = prediction_data["away_team"]

        home_margin = prediction_data["home_margin"]
        away_margin = prediction_data["away_margin"]

        # predicted_margin is always positive as its always associated with predicted_winner
        predicted_margin = np.mean(np.abs([home_margin, away_margin]))

        if predicted_margin > away_margin:
            predicted_winner = home_team
        elif away_margin > predicted_margin:
            predicted_winner = away_team
        else:
            raise ValueError(
                "Predicted home and away margins are equal, which is basically "
                "impossible, so figure out what's going on:\n"
                f"{prediction_data}"
            )

        matches = Match.objects.get(
            start_date_time__year=prediction_data["year"],
            round_number=prediction_data["round_number"],
            teammatch__team__name__in=[home_team, away_team],
        )

        if len(matches) != 2 or matches[0] != matches[1]:
            raise ValueError(
                "Prediction data should have yielded a unique match, with duplicates "
                "returned from the DB, but we got the following instead:\n"
                f"{matches.values('round_number', 'start_date_time')}\n\n"
                f"{prediction_data}"
            )

        match = matches.first()
        ml_model = MLModel.objects.get(name=prediction_data["ml_model"])

        prediction_attributes = {"match": match, "ml_model": ml_model}

        try:
            prediction = Prediction.objects.get(**prediction_attributes)

            prediction.predicted_margin = predicted_margin
            prediction.predicted_winner = predicted_winner

            prediction.clean_fields()
            prediction.clean()
            prediction.save()

            return None
        except Prediction.DoesNotExist:
            prediction = Prediction(
                predicted_margin=predicted_margin,
                predicted_winner=predicted_winner,
                **prediction_attributes,
            )

            return prediction

    @staticmethod
    def __build_team_match(
        match: Match, match_data: CleanedFixtureData
    ) -> Optional[List[TeamMatch]]:
        team_match_count = match.teammatch_set.count()

        if team_match_count == 2:
            return None

        if team_match_count == 1 or team_match_count > 2:
            model_string = "TeamMatches" if team_match_count > 1 else "TeamMatch"
            raise ValueError(
                f"{match} has {team_match_count} associated {model_string}, which shouldn't "
                "happen. Figure out what's up."
            )
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
