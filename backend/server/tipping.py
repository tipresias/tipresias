"""Module for handling generation and saving of tips (i.e. predictions)."""

from datetime import datetime
from typing import List, Optional, Dict, Tuple
import os
from warnings import warn

import pandas as pd
import numpy as np
from splinter import Browser
from splinter.driver import ElementAPI
from django.utils import timezone
from django.conf import settings

from server.models import Match, TeamMatch, Prediction
from server.types import FixtureData
from server import data_import
from server.helpers import pivot_team_matches_to_matches


FIRST_ROUND = 1
JAN = 1
FIRST = 1

# Footytips has some different naming conventions from everyone else,
# so we have to convert a few team names to match how they're displayed on the site
FT_TEAM_TRANSLATIONS = {
    "GWS": "GWS Giants",
    "Brisbane": "Brisbane Lions",
    "West Coast": "West Coast Eagles",
}


class Tipping:
    """Handles generation and saving of tips (i.e. predictions)."""

    def __init__(
        self,
        fetch_data=True,
        data_importer=data_import,
        ml_models=None,
        submit_tips=True,
    ) -> None:
        """
        Instantiate a Tipping object.

        Params:
        -------
        fetch_data: Whether to fetch up-to-date data or load saved data files.
        data_importer: Module used for importing data from remote sources.
        ml_models: Which models to use when making tipping predictions.
        submit_tips: Whether to submit the tips to the relevant competition websites.
        """
        self.right_now = timezone.localtime()
        self.current_year = self.right_now.year
        self.fetch_data = fetch_data
        self.data_importer = data_importer
        self.ml_models = ml_models
        self.submit_tips = submit_tips
        self.verbose = 0

    def tip(self, verbose=1) -> None:
        """Fetch and save predictions, then submit tips to competitions."""
        self.verbose = verbose  # pylint: disable=W0201
        self.data_importer.verbose = verbose

        fixture_data_frame = self._fetch_fixture_data(self.current_year)
        upcoming_round, upcoming_matches = self._select_upcoming_matches(
            fixture_data_frame
        )

        if upcoming_round is None or upcoming_matches is None:
            self._backfill_match_results()
            return None

        self._create_matches(
            upcoming_matches.replace({np.nan: None}).to_dict("records"), upcoming_round
        )

        upcoming_round_year = upcoming_matches["date"].max().year

        self._make_predictions(upcoming_round_year, upcoming_round)
        self._backfill_match_results()

        if self.submit_tips:
            self._submit_tips()

        return None

    def _fetch_fixture_data(self, year: int) -> pd.DataFrame:
        if self.verbose == 1:
            print(f"Fetching fixture for {year}...\n")

        fixture_data_frame = self.data_importer.fetch_fixture_data(
            start_date=timezone.make_aware(datetime(year, 1, 1)),
            end_date=timezone.make_aware(datetime(year, 12, 31)),
        )

        if not fixture_data_frame.any().any():
            return fixture_data_frame

        return fixture_data_frame

    def _select_upcoming_matches(
        self, fixture_data_frame: pd.DataFrame
    ) -> Tuple[Optional[int], Optional[pd.DataFrame]]:
        if not fixture_data_frame.any().any():
            warn(
                "Fixture for the upcoming round haven't been posted yet, "
                "so there's nothing to tip. Try again later."
            )

            return None, None

        latest_match_date = fixture_data_frame["date"].max()

        if self.right_now > latest_match_date:
            warn(
                f"No matches found after {self.right_now}. The latest match "
                f"found is at {latest_match_date}\n"
            )

            return None, None

        upcoming_round = (
            fixture_data_frame.query("date > @self.right_now")
            .loc[:, "round_number"]
            .min()
        )
        fixture_for_upcoming_round = fixture_data_frame.query(
            "round_number == @upcoming_round"
        )

        return upcoming_round, fixture_for_upcoming_round

    def _create_matches(
        self, fixture_data: List[FixtureData], upcoming_round: int
    ) -> None:
        saved_match_count = Match.objects.filter(
            start_date_time__gt=self.right_now, round_number=upcoming_round
        ).count()

        if saved_match_count > 0:
            if self.verbose == 1:
                print(
                    f"{saved_match_count} unplayed match records found for round {upcoming_round}. "
                    "Updating associated prediction records with new model predictions.\n"
                )

            return None

        if self.verbose == 1:
            print(
                f"Creating new Match and TeamMatch records for round {upcoming_round}..."
            )

        assert any(fixture_data), "No fixture data found."

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

        for fixture_datum in fixture_data:
            self._build_match(fixture_datum)

        if self.verbose == 1:
            print("Match data saved!\n")

        return None

    @staticmethod
    def _build_match(match_data: FixtureData) -> Tuple[TeamMatch, TeamMatch]:
        match = Match.get_or_create_from_raw_data(match_data)

        return TeamMatch.get_or_create_from_raw_data(match, match_data)

    def _make_predictions(self, year: int, round_number: int) -> None:
        if self.verbose == 1:
            print("Saving prediction records...")

        predictions = self.data_importer.fetch_prediction_data(
            (year, year + 1), round_number=round_number, ml_models=self.ml_models
        )
        home_away_df = pivot_team_matches_to_matches(predictions)

        for pred in home_away_df.replace({np.nan: None}).to_dict("records"):
            Prediction.update_or_create_from_raw_data(pred)

        if self.verbose == 1:
            print("Predictions saved!\n")

    def _backfill_match_results(self) -> None:
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

    def _submit_tips(self) -> None:
        print("Submitting tips to footytips.com.au...")

        browser = Browser("firefox", headless=True)
        self._log_in(browser)

        predictions = self._get_latest_round_predictions()
        match_elements = browser.find_by_css(".tipping-container")

        self._fill_in_tipping_form(predictions, match_elements)
        browser.find_by_css(".tipform-submit-button").first.click()

        print("Tips submitted!")

    def _get_latest_round_predictions(self) -> Dict[str, int]:
        latest_match = Match.objects.latest("start_date_time")
        latest_year = latest_match.start_date_time.year
        latest_round = latest_match.round_number

        latest_round_predictions = (
            Prediction.objects.filter(
                ml_model__name=settings.PRINCIPLE_ML_MODEL,
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
            self._translate_team_name(pred["predicted_winner__name"]): pred[
                "predicted_margin"
            ]
            for pred in latest_round_predictions
        }

    @staticmethod
    def _translate_team_name(team_name: str) -> str:
        if team_name not in FT_TEAM_TRANSLATIONS:
            return team_name

        return FT_TEAM_TRANSLATIONS[team_name]

    @staticmethod
    def _log_in(browser):
        browser.visit("https://www.footytips.com.au/tipping/afl/")

        # Have to use second login form, because the first is some invisible Angular
        # something something
        login_form = browser.find_by_name("frmLogin")[1]
        login_form.find_by_name("userLogin").fill(os.getenv("FOOTY_TIPS_USERNAME", ""))
        login_form.find_by_name("userPassword").fill(
            os.getenv("FOOTY_TIPS_PASSWORD", "")
        )
        login_form.find_by_id("signin-ft").click()

    def _fill_in_tipping_form(
        self, predictions: Dict[str, int], match_elements: ElementAPI
    ):
        for match_element in match_elements:
            predicted_winner, predicted_margin = self._get_match_prediction(
                predictions, match_element
            )

            if predicted_winner is None or predicted_margin is None:
                warn(
                    "No matching prediction was found for a match element. "
                    "This likely means that the tip submission page has not been "
                    "updated for the next round yet. Try again tomorrow."
                )

                return None

            self._select_predicted_winner(predicted_winner, match_element)
            self._fill_in_predicted_margin(predicted_margin, match_element)

            return None

    @staticmethod
    def _get_match_prediction(
        predictions: Dict[str, int], match_element: ElementAPI
    ) -> Tuple[Optional[str], Optional[int]]:
        for team_name in predictions.keys():
            if team_name in match_element.text:
                return (team_name, predictions[team_name])

        return None, None

    @staticmethod
    def _select_predicted_winner(
        predicted_winner: str, match_element: ElementAPI
    ) -> None:
        team_matches = match_element.find_by_css(".tip-selection")

        for team_match in team_matches:
            team_match_input = team_match.find_by_css(".radio-button")

            if predicted_winner in team_match.text and team_match_input.visible:
                team_match_input.click()

    @staticmethod
    def _fill_in_predicted_margin(
        predicted_margin: int, match_element: ElementAPI
    ) -> None:
        margin_input = match_element.find_by_name("Margin")

        if any(margin_input):
            margin_input.fill(predicted_margin)
