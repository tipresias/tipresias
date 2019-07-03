"""Module for 'tip' command that updates predictions for upcoming AFL matches"""

from functools import reduce
from datetime import datetime, date
from typing import List, Optional
from django.core.management.base import BaseCommand
from django import utils
import pandas as pd

from project.settings.common import MELBOURNE_TIMEZONE
from server.models import Match, TeamMatch, Team, Prediction
from server.types import CleanFixtureData
from server import data_import
from server.helpers import pivot_team_matches_to_matches


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
        fetch_data=True,
        data_importer=data_import,
        ml_models=None,
        **kwargs,
    ) -> None:
        super().__init__(*args, **kwargs)

        self.right_now = datetime.now(tz=MELBOURNE_TIMEZONE)
        self.current_year = self.right_now.year
        self.fetch_data = fetch_data
        self.data_importer = data_importer
        self.ml_models = ml_models

    def handle(self, *_args, verbose=1, **_kwargs) -> None:  # pylint: disable=W0221
        """Run 'tip' command"""

        self.verbose = verbose  # pylint: disable=W0201
        self.data_importer.verbose = verbose

        fixture_data_frame = self.__fetch_fixture_data(self.current_year)
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
        self.__backfill_match_results()

    def __fetch_fixture_data(self, year: int) -> pd.DataFrame:
        if self.verbose == 1:
            print(f"Fetching fixture for {year}...\n")

        fixture_data_frame = self.data_importer.fetch_fixture_data(
            start_date=f"{year}-01-01", end_date=f"{year}-12-31"
        )

        latest_match = fixture_data_frame["date"].max()

        if self.right_now > latest_match:
            raise ValueError(
                f"No matches found after {self.right_now}. The latest match found is "
                f"at {latest_match}\n"
            )

        return fixture_data_frame

    def __create_matches(self, fixture_data: List[CleanFixtureData]) -> None:
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

    def __build_match(self, match_data: CleanFixtureData) -> Optional[List[TeamMatch]]:
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
        predictions = self.data_importer.fetch_prediction_data(
            (year, year + 1), round_number=round_number, ml_models=self.ml_models
        )
        home_away_df = pivot_team_matches_to_matches(predictions)

        for pred in home_away_df.to_dict("records"):
            Prediction.update_or_create_from_data(pred)

        if self.verbose == 1:
            print("Predictions saved!\n")

    def __backfill_match_results(self) -> None:
        matches_without_results = Match.objects.prefetch_related(
            "teammatch_set", "prediction_set"
        ).filter(start_date_time__lt=self.right_now, teammatch__score=0)

        if matches_without_results.count() == 0:
            return None

        match_results = self.__fetch_match_results_to_fill(matches_without_results)

        for match in matches_without_results:
            self.__update_played_match_scores(match_results, match)
            self.__update_predictions_correctness(match)

        return None

    def __fetch_match_results_to_fill(self, matches_without_results) -> pd.DataFrame:
        earliest_match_date = matches_without_results.earliest(
            "start_date_time"
        ).start_date_time

        return self.data_importer.fetch_match_results_data(
            str(earliest_match_date.date()),
            str(self.right_now.date()),
            fetch_data=self.fetch_data,
        )

    @staticmethod
    def __update_played_match_scores(match_results: pd.DataFrame, match: Match) -> None:
        home_team_match = match.teammatch_set.get(at_home=True)
        away_team_match = match.teammatch_set.get(at_home=False)

        match_result = match_results.query(
            "year == @match.start_date_time.year & "
            "round_number == @match.round_number & "
            "home_team == @home_team_match.team.name & "
            "away_team == @away_team_match.team.name"
        )

        if len(match_result) != 1:
            raise ValueError(
                "Filtering match results by year, round_number and team name "
                "should result in a single row, but instead the following was "
                "returned:\n"
                f"{match_result}"
            )

        match_result = match_result.iloc[0, :]

        home_team_match.score = match_result["home_score"]
        home_team_match.clean()
        home_team_match.save()

        away_team_match.score = match_result["away_score"]
        away_team_match.clean()
        away_team_match.save()

    @staticmethod
    def __update_predictions_correctness(match: Match) -> None:
        for prediction in match.prediction_set.all():
            prediction.is_correct = Prediction.calculate_whether_correct(
                match, prediction.predicted_winner
            )
            prediction.clean()
            prediction.save()

    @staticmethod
    def __build_team_match(
        match: Match, match_data: CleanFixtureData
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
