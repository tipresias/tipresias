"""Module for handling generation and saving of tips (i.e. predictions)."""

from datetime import datetime
from typing import List, Optional, Dict, Tuple, Union, Literal, cast, Any
import os
from warnings import warn

import pandas as pd
import numpy as np
from splinter import Browser
from splinter.driver import ElementAPI
from django.utils import timezone
from django.conf import settings
from mypy_extensions import TypedDict

from server.models import Match, TeamMatch, Prediction
from server.types import FixtureData
from server import data_import
from server.helpers import pivot_team_matches_to_matches
from project.settings.data_config import TEAM_TRANSLATIONS


PredictedWinner = TypedDict(
    "PredictedWinner",
    {
        "predicted_winner__name": str,
        "predicted_margin": int,
        "predicted_win_probability": float,
    },
)
PredictionType = Union[
    Literal["predicted_margin"], Literal["predicted_win_probability"]
]


FIRST_ROUND = 1
JAN = 1
FIRST = 1


# There's also a 'gaussian' competition, but I don't participate in that one,
# so leaving it out for now.
SUPPORTED_MONASH_COMPS = ["normal", "info"]
MODELS_FOR_COMPETITIONS = [settings.PRINCIPLE_ML_MODEL, "confidence_estimator"]


class MonashSubmitter:
    """Submits tips to one or more of the Monash footy tipping competitions."""

    def __init__(  # pylint: disable=dangerous-default-value
        self,
        competitions: List[str] = ["normal", "info"],
        browser=Browser("firefox", headless=True),
        verbose: int = 1,
    ):
        """
        Instantiate a MonashSubmitter object.

        Params:
        -------
        competitions: Names of the different Monash competitions.
            Based on the option value of the select input for logging into
            a competition.
        verbose: How much information to print. 1 prints all messages; 0 prints none.
        """
        self.competitions = competitions
        self.browser = browser
        self.verbose = verbose

    def submit_tips(  # pylint: disable=dangerous-default-value
        self, predicted_winners: List[PredictedWinner],
    ) -> None:
        """Submit tips to probabilistic-footy.monash.edu.

        Params:
        -------
        predicted_winners: A dict where the keys are team names and the values
            are their predicted margins. Only includes predicted winners.
        """

        if self.verbose == 1:
            print("Submitting tips to probabilistic-footy.monash.edu...")

        for comp in self.competitions:
            assert comp in SUPPORTED_MONASH_COMPS

            # Need to revisit home page for each competition, because submitting tips
            # doesn't redirect back to it.
            self.browser.visit(
                "http://probabilistic-footy.monash.edu/~footy/tips.shtml"
            )
            self._login(comp)
            self._fill_in_tipping_form(
                self._transform_into_tipping_input(predicted_winners, comp)
            )

            self._submit_form()

            if self.verbose == 1:
                print("Tips submitted!")

    @staticmethod
    def _transform_into_tipping_input(
        predicted_winners: List[PredictedWinner], competition
    ) -> Dict[str, Union[int, float]]:
        PREDICTION_TYPE = {"normal": "margin", "info": "win_probability"}
        competition_prediction_type = cast(
            PredictionType, f"predicted_{PREDICTION_TYPE[competition]}",
        )

        return {
            predicted_winner["predicted_winner__name"]: predicted_winner[
                competition_prediction_type
            ]
            for predicted_winner in predicted_winners
            if predicted_winner[competition_prediction_type] is not None
        }

    def _login(self, competition: str) -> None:
        login_form = self.browser.find_by_css("form")

        login_form.find_by_name("name").fill(os.getenv("MONASH_USERNAME", ""))
        login_form.find_by_name("passwd").fill(os.getenv("MONASH_PASSWORD", ""))
        login_form.select("comp", competition)
        # There's a round number select, but we don't need to change it,
        # because it defaults to the upcoming/current round on page load.
        login_form.find_by_css("input[type=submit]").click()

    def _fill_in_tipping_form(self, predicted_winners: Dict[str, Union[int, float]]):
        tip_table = self.browser.find_by_css("form table")
        table_rows = tip_table.find_by_css("tr")

        assert len(table_rows) == len(predicted_winners), (
            "The number of predicted winners doesn't match the number of matches. "
            "Check the given predicted winners below:\n"
            f"{predicted_winners}"
        )

        for table_row in table_rows:
            self._enter_prediction(predicted_winners, table_row)

    def _enter_prediction(self, predicted_winners, table_row) -> None:
        for row_input in table_row.find_by_css("input"):
            predicted_winner = None
            team_name = self._translate_team_name(row_input.text)

            if team_name in predicted_winners.keys():
                row_input.click()
                predicted_winner = row_input.text

            if row_input.value.isnumeric():
                row_input.fill(predicted_winners[predicted_winner])

    @staticmethod
    def _translate_team_name(element_text: str) -> str:
        if element_text in TEAM_TRANSLATIONS.keys():
            return TEAM_TRANSLATIONS[element_text]

        return element_text

    def _submit_form(self):
        self.browser.find_by_css("input[type=submit]").click()


class FootyTipsSubmitter:
    """Submits tips to the tipping competition on footytips.com.au."""

    def __init__(self, browser=Browser("firefox", headless=True), verbose: int = 1):
        """
        Instantiate a FootyTipsSubmitter object.

        Params:
        -------
        verbose: How much information to print. 1 prints all messages; 0 prints none.
        """
        self.browser = browser
        self.verbose = verbose

    def submit_tips(self, predicted_winners: List[PredictedWinner]) -> None:
        """
        Submit tips to footytips.com.au.

        Params:
        -------
        predicted_winners: A dict where the keys are team names and the values
            are their predicted margins. Only includes predicted winners.
        """
        if self.verbose == 1:
            print("Submitting tips to footytips.com.au...")

        self._log_in()

        self._fill_in_tipping_form(
            self._transform_into_tipping_input(predicted_winners)
        )
        self._submit_form()

        if self.verbose == 1:
            print("Tips submitted!")

    def _transform_into_tipping_input(
        self, predicted_winners: List[PredictedWinner]
    ) -> Dict[str, int]:
        return {
            self._translate_team_name(
                predicted_winner["predicted_winner__name"]
            ): predicted_winner["predicted_margin"]
            for predicted_winner in predicted_winners
            if predicted_winner["predicted_margin"] is not None
        }

    def _log_in(self):
        self.browser.visit("https://www.footytips.com.au/tipping/afl/")

        # Have to use second login form, because the first is some invisible Angular
        # something something
        login_form = self.browser.find_by_name("frmLogin")[1]
        login_form.find_by_name("userLogin").fill(os.getenv("FOOTY_TIPS_USERNAME", ""))
        login_form.find_by_name("userPassword").fill(
            os.getenv("FOOTY_TIPS_PASSWORD", "")
        )
        login_form.find_by_id("signin-ft").click()

    def _fill_in_tipping_form(self, predicted_winners: Dict[str, int]):
        match_elements = self.browser.find_by_css(".tipping-container")

        assert len(match_elements) == len(predicted_winners), (
            "The number of predicted winners doesn't match the number of matches. "
            "Check the given predicted winners below:\n"
            f"{predicted_winners}"
        )

        for match_element in match_elements:
            predicted_winner, predicted_margin = self._get_match_prediction(
                predicted_winners, match_element
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

    def _select_predicted_winner(
        self, predicted_winner: str, match_element: ElementAPI
    ) -> None:
        for team_name_element in match_element.find_by_css(".team-name.team-full"):
            if (
                self._translate_team_name(team_name_element.text) == predicted_winner
                and team_name_element.visible
            ):
                # Even though it's not an input element, triggering a click
                # on the team name still triggers the associated radio button.
                team_name_element.click()

    @staticmethod
    def _translate_team_name(element_text: str) -> str:
        if element_text in TEAM_TRANSLATIONS.keys():
            return TEAM_TRANSLATIONS[element_text]

        return element_text

    @staticmethod
    def _fill_in_predicted_margin(
        predicted_margin: int, match_element: ElementAPI
    ) -> None:
        margin_input = match_element.find_by_name("Margin")

        if any(margin_input):
            margin_input.fill(predicted_margin)

    def _submit_form(self):
        self.browser.find_by_css(".tipform-submit-button").first.click()


class Tipper:
    """Handles generation and saving of tips (i.e. predictions)."""

    def __init__(  # pylint: disable=dangerous-default-value
        self,
        fetch_data: bool = True,
        data_importer=data_import,
        tip_submitters: List[Any] = [FootyTipsSubmitter(), MonashSubmitter()],
        ml_models: Optional[List[str]] = None,
    ) -> None:
        """
        Instantiate a Tipping object.

        Params:
        -------
        fetch_data: Whether to fetch up-to-date data or load saved data files.
        data_importer: Module used for importing data from remote sources.
        ml_models: A list of names of models to use when making tipping predictions.
        submit_tips: Whether to submit the tips to the relevant competition websites.
        """
        self.fetch_data = fetch_data
        self.data_importer = data_importer
        self.tip_submitters = tip_submitters
        self.ml_models = ml_models

        self._right_now = timezone.localtime()
        self.verbose: int = 0

    def tip(self, verbose=1) -> None:
        """
        Fetch and save predictions, then submit tips to competitions.

        Params:
        -------
        verbose: How much information to print. 1 prints all messages; 0 prints none.
        """
        self.verbose = verbose  # pylint: disable=W0201

        fixture_data_frame = self._fetch_fixture_data(self._right_now.year)
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

        for submitter in self.tip_submitters:
            submitter.verbose = self.verbose
            submitter.submit_tips(self._get_predicted_winners_for_latest_round())

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

        if self._right_now > latest_match_date:
            warn(
                f"No matches found after {self._right_now}. The latest match "
                f"found is at {latest_match_date}\n"
            )

            return None, None

        upcoming_round = (
            fixture_data_frame.query("date > @self._right_now")
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
            start_date_time__gt=self._right_now, round_number=upcoming_round
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
            earliest_date_without_results, self._right_now, fetch_data=self.fetch_data
        )

        if not any(match_results):
            print("Results data is not yet available to update match records.")
            return None

        Match.update_results(match_results)

        return None

    @staticmethod
    def _get_predicted_winners_for_latest_round() -> List[PredictedWinner]:
        latest_match = Match.objects.latest("start_date_time")
        latest_year = latest_match.start_date_time.year
        latest_round = latest_match.round_number

        latest_round_predictions = (
            Prediction.objects.filter(
                ml_model__name__in=MODELS_FOR_COMPETITIONS,
                match__start_date_time__gt=timezone.make_aware(
                    datetime(latest_year, JAN, FIRST)
                ),
                match__round_number=latest_round,
            )
            .select_related("match")
            .prefetch_related("match__teammatch_set__team")
            .values(
                "predicted_winner__name",
                "predicted_margin",
                "predicted_win_probability",
            )
        )

        assert any(
            latest_round_predictions
        ), f"No predictions found for round {latest_round}."

        return latest_round_predictions
