"""Module for handling generation and saving of tips (i.e. predictions)"""

from functools import reduce
from datetime import datetime, date, timedelta
from typing import List, Optional, Dict, Tuple
import os
from warnings import warn
import pytz

import pandas as pd
from splinter import Browser
from splinter.driver import ElementAPI

from server.models import Match, TeamMatch, Team, Prediction
from server.types import CleanFixtureData
from server import data_import
from server.helpers import pivot_team_matches_to_matches


NO_SCORE = 0
FIRST_ROUND = 1
# We calculate rolling sums/means for some features that can span over 5 seasons
# of data, so we're setting it to 10 to be on the safe side.
N_SEASONS_FOR_PREDICTION = 10
# We want to limit the amount of data loaded as much as possible,
# because we only need the full data set for model training and data analysis,
# and we want to limit memory usage and speed up data processing for tipping
PREDICTION_DATA_START_DATE = f"{date.today().year - N_SEASONS_FOR_PREDICTION}-01-01"

WEEK_IN_DAYS = 7
JAN = 1
FIRST = 1

# Footytips has some different naming conventions from everyone else,
# so we have to convert a few team names to match how they're displayed on the site
FT_TEAM_TRANSLATIONS = {
    "GWS": "GWS Giants",
    "Brisbane": "Brisbane Lions",
    "West Coast": "West Coast Eagles",
}

# TODO: Along with SeedDb command, this is in serious need of a refactor.
# The data fetching isn't too bad, but the DB record CRUD should be moved
# to the relevant model classes (same goes for SeedDb). submit_tips should
# probably be a public method rather than a private one that gets called inside tip
class Tipping:
    """Handles generation and saving of tips (i.e. predictions)"""

    def __init__(
        self,
        fetch_data=True,
        data_importer=data_import,
        ml_models=None,
        submit_tips=True,
    ) -> None:
        self.right_now = datetime.now(tz=pytz.UTC)
        self.current_year = self.right_now.year
        self.fetch_data = fetch_data
        self.data_importer = data_importer
        self.ml_models = ml_models
        self.submit_tips = submit_tips

    def tip(self, verbose=1) -> None:
        """Run 'tip' command"""

        self.verbose = verbose  # pylint: disable=W0201
        self.data_importer.verbose = verbose

        fixture_data_frame = self.__fetch_fixture_data(self.current_year)

        if not fixture_data_frame.any().any():
            if self.verbose == 1:
                print(
                    "Fixture for the upcoming round haven't been posted yet, "
                    "so there's nothing to tip. Try again later."
                )

            return None

        upcoming_round = (
            fixture_data_frame.query("date > @self.right_now")
            .loc[:, "round_number"]
            .min()
        )
        fixture_for_upcoming_round = fixture_data_frame.query(
            "round_number == @upcoming_round"
        )

        saved_match_count = Match.objects.filter(
            start_date_time__gt=self.right_now, round_number=upcoming_round
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

            self.__create_matches(fixture_for_upcoming_round.to_dict("records"))
        else:
            if self.verbose == 1:
                print(
                    f"{saved_match_count} unplayed match records found for round {upcoming_round}. "
                    "Updating associated prediction records with new model predictions.\n"
                )

        upcoming_round_year = (
            fixture_for_upcoming_round["date"].map(lambda x: x.year).max()
        )

        if self.verbose == 1:
            print("Saving prediction records...")

        self.__make_predictions(upcoming_round_year, upcoming_round)

        if self.verbose == 1:
            print("Filling in results for recent matches...")

        self.__backfill_match_results()

        if self.submit_tips:
            self.__submit_tips()

        return None

    def __fetch_fixture_data(self, year: int) -> pd.DataFrame:
        if self.verbose == 1:
            print(f"Fetching fixture for {year}...\n")

        fixture_data_frame = self.data_importer.fetch_fixture_data(
            start_date=f"{year}-01-01", end_date=f"{year}-12-31"
        )

        if not fixture_data_frame.any().any():
            return fixture_data_frame

        latest_match_date = fixture_data_frame["date"].max()

        if self.right_now > latest_match_date:
            raise ValueError(
                f"No matches found after {self.right_now}. The latest match found is "
                f"at {latest_match_date}\n"
            )

        return fixture_data_frame

    def __create_matches(self, fixture_data: List[CleanFixtureData]) -> None:
        if not any(fixture_data):
            raise ValueError("No fixture data found.")

        round_number = {match_data["round_number"] for match_data in fixture_data}.pop()
        year = {match_data["year"] for match_data in fixture_data}.pop()

        prev_match = Match.objects.order_by("-start_date_time").first()

        if prev_match is not None:
            assert round_number in (prev_match.round_number + 1, FIRST_ROUND), (
                "Expected upcoming round number to be 1 greater than previous round "
                f"or 1, but upcoming round is {round_number} in {year}, "
                f" and previous round was {prev_match.round_number} "
                f"in {prev_match.start_date_time.year}"
            )

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

        # Fiddling with timezones is proving error-prone, so I'm just creating
        # a new datetime based on the raw one
        match_date = datetime(
            raw_date.year,
            raw_date.month,
            raw_date.day,
            raw_date.hour,
            raw_date.minute,
            tzinfo=pytz.UTC,
        )

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

        if not any(match_results):
            return None

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

    def __update_played_match_scores(
        self, match_results: pd.DataFrame, match: Match
    ) -> None:
        home_team_match = match.teammatch_set.get(at_home=True)
        away_team_match = match.teammatch_set.get(at_home=False)

        match_result = match_results.query(
            "year == @match.start_date_time.year & "
            "round_number == @match.round_number & "
            "home_team == @home_team_match.team.name & "
            "away_team == @away_team_match.team.name"
        )

        # AFLTables usually updates match results a few days after the round
        # is finished. Allowing for the occasional delay, we accept matches without
        # results data for a week before raising an error.
        if (
            match.start_date_time > self.right_now - timedelta(days=WEEK_IN_DAYS)
            and not match_results.any().any()
        ):
            warn(
                f"Unable to update the match between {home_team_match.team.name} "
                f"and {away_team_match.team.name} from round {match.round_number}. "
                "This is likely due to AFLTables not having updated the match results "
                "yet."
            )

            return None

        match_values = match.teammatch_set.values(
            "match__start_date_time",
            "match__round_number",
            "match__venue",
            "team__name",
            "at_home",
        )
        assert match_results.any().any(), (
            "Didn't find any match data rows that matched match record:\n"
            f"{match_values}"
        )

        assert len(match_result) == 1, (
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

        return None

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

    def __submit_tips(self) -> None:
        print("Submitting tips to footytips.com.au...")

        browser = Browser("firefox", headless=True)
        self.__log_in(browser)

        predictions = self.__get_latest_round_predictions()
        match_elements = browser.find_by_css(".tipping-container")

        self.__fill_in_tipping_form(predictions, match_elements)
        browser.find_by_css(".tipform-submit-button").first.click()

        print("Tips submitted!")

    def __get_latest_round_predictions(self) -> Dict[str, int]:
        latest_match = Match.objects.latest("start_date_time")
        latest_year = latest_match.start_date_time.year
        latest_round = latest_match.round_number

        latest_round_predictions = (
            Prediction.objects.filter(
                ml_model__name="tipresias",
                match__start_date_time__gt=datetime(
                    latest_year, JAN, FIRST, tzinfo=pytz.UTC
                ),
                match__round_number=latest_round,
            )
            .select_related("match")
            .prefetch_related("match__teammatch_set__team")
            .values("predicted_winner__name", "predicted_margin")
        )

        assert any(
            latest_round_predictions
        ), f"No predictions found for round {latest_round}."

        return {
            self.__translate_team_name(pred["predicted_winner__name"]): pred[
                "predicted_margin"
            ]
            for pred in latest_round_predictions
        }

    @staticmethod
    def __translate_team_name(team_name: str) -> str:
        if team_name not in FT_TEAM_TRANSLATIONS:
            return team_name

        return FT_TEAM_TRANSLATIONS[team_name]

    @staticmethod
    def __log_in(browser):
        browser.visit("https://www.footytips.com.au/tipping/afl/")

        # Have to use second login form, because the first is some invisible Angular
        # something something
        login_form = browser.find_by_name("frmLogin")[1]
        login_form.find_by_name("userLogin").fill(os.getenv("FOOTY_TIPS_USERNAME", ""))
        login_form.find_by_name("userPassword").fill(
            os.getenv("FOOTY_TIPS_PASSWORD", "")
        )
        login_form.find_by_id("signin-ft").click()

    def __fill_in_tipping_form(
        self, predictions: Dict[str, int], match_elements: ElementAPI
    ):
        for match_element in match_elements:
            predicted_winner, predicted_margin = self.__get_match_prediction(
                predictions, match_element
            )

            if predicted_winner is None or predicted_margin is None:
                warn(
                    "No matching prediction was found for a match element. "
                    "This likely means that the tip submission page has not been "
                    "updated for the next round yet. Try again tomorrow."
                )

                return None

            self.__select_predicted_winner(predicted_winner, match_element)
            self.__fill_in_predicted_margin(predicted_margin, match_element)

            return None

    @staticmethod
    def __get_match_prediction(
        predictions: Dict[str, int], match_element: ElementAPI
    ) -> Tuple[Optional[str], Optional[int]]:
        for team_name in predictions.keys():
            if team_name in match_element.text:
                return (team_name, predictions[team_name])

        return None, None

    @staticmethod
    def __select_predicted_winner(
        predicted_winner: str, match_element: ElementAPI
    ) -> None:
        team_matches = match_element.find_by_css(".tip-selection")

        for team_match in team_matches:
            team_match_input = team_match.find_by_css(".radio-button")

            if predicted_winner in team_match.text and team_match_input.visible:
                team_match_input.click()

    @staticmethod
    def __fill_in_predicted_margin(
        predicted_margin: int, match_element: ElementAPI
    ) -> None:
        margin_input = match_element.find_by_name("Margin")

        if any(margin_input):
            margin_input.fill(predicted_margin)
