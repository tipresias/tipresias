"""Module for handling generation and saving of tips (i.e. predictions)"""

from datetime import datetime, date
from typing import List, Optional, Dict, Tuple
import os
from warnings import warn

import pandas as pd
from splinter import Browser
from splinter.driver import ElementAPI
from django.utils import timezone

from server.models import Match, TeamMatch, Prediction
from server.types import FixtureData
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
        self.right_now = timezone.localtime()
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
            warn(
                "Fixture for the upcoming round haven't been posted yet, "
                "so there's nothing to tip. Try again later."
            )

            self.__backfill_match_results()

            return None

        latest_match_date = fixture_data_frame["date"].max()

        if self.right_now > latest_match_date:
            warn(
                f"No matches found after {self.right_now}. The latest match "
                f"found is at {latest_match_date}\n"
            )

            self.__backfill_match_results()

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

            self.__create_matches(
                fixture_for_upcoming_round.to_dict("records"), upcoming_round
            )
        else:
            if self.verbose == 1:
                print(
                    f"{saved_match_count} unplayed match records found for round {upcoming_round}. "
                    "Updating associated prediction records with new model predictions.\n"
                )

        upcoming_round_year = (
            fixture_for_upcoming_round["date"].map(lambda x: x.year).max()
        )

        self.__make_predictions(upcoming_round_year, upcoming_round)
        self.__backfill_match_results()

        if self.submit_tips:
            self.__submit_tips()

        return None

    def __fetch_fixture_data(self, year: int) -> pd.DataFrame:
        if self.verbose == 1:
            print(f"Fetching fixture for {year}...\n")

        fixture_data_frame = self.data_importer.fetch_fixture_data(
            start_date=timezone.make_aware(datetime(year, 1, 1)),
            end_date=timezone.make_aware(datetime(year, 12, 31)),
        )

        if not fixture_data_frame.any().any():
            return fixture_data_frame

        return fixture_data_frame

    def __create_matches(
        self, fixture_data: List[FixtureData], upcoming_round: int
    ) -> None:
        if self.verbose == 1:
            print(f"Saving Match and TeamMatch records for round {upcoming_round}...")

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

        build_matches = (
            self.__build_match(fixture_datum) for fixture_datum in fixture_data
        )
        list(build_matches)

        if self.verbose == 1:
            print("Match data saved!\n")

    @staticmethod
    def __build_match(match_data: FixtureData) -> Tuple[TeamMatch, TeamMatch]:
        match = Match.get_or_create_from_raw_data(match_data)

        return TeamMatch.get_or_create_from_raw_data(match, match_data)

    def __make_predictions(self, year: int, round_number: int) -> None:
        if self.verbose == 1:
            print("Saving prediction records...")

        predictions = self.data_importer.fetch_prediction_data(
            (year, year + 1), round_number=round_number, ml_models=self.ml_models
        )
        home_away_df = pivot_team_matches_to_matches(predictions)

        for pred in home_away_df.to_dict("records"):
            Prediction.update_or_create_from_data(pred)

        if self.verbose == 1:
            print("Predictions saved!\n")

    def __backfill_match_results(self) -> None:
        if self.verbose == 1:
            print("Filling in results for recent matches...")

        earliest_date_without_results = Match.earliest_date_without_results()

        if earliest_date_without_results is None:
            if self.verbose == 1:
                print("No played matches are missing results.")

            return None

        match_results = self.data_importer.fetch_match_results_data(
            earliest_date_without_results, self.right_now, fetch_data=self.fetch_data
        )

        if not any(match_results):
            print("Results data is not yet available to update match records.")
            return None

        Match.update_results(match_results)

        return None

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
                match__start_date_time__gt=timezone.make_aware(
                    datetime(latest_year, JAN, FIRST)
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
