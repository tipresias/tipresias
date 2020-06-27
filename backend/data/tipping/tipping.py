"""Module for handling generation and saving of tips (i.e. predictions)."""

from datetime import datetime
from typing import List, Optional, Dict, Tuple, Union, Literal, cast, Any
import os
from warnings import warn
import re

import pandas as pd
import numpy as np
from django.utils import timezone
from django.conf import settings
from mypy_extensions import TypedDict
import mechanicalsoup
import requests

from data import data_import
from data.helpers import pivot_team_matches_to_matches
from server import api
from project.settings.data_config import TEAM_TRANSLATIONS


PredictedWinner = TypedDict(
    "PredictedWinner",
    {
        "predicted_winner__name": str,
        "predicted_margin": float,
        "predicted_win_probability": float,
    },
)
PredictionType = Union[
    Literal["predicted_margin"], Literal["predicted_win_probability"]
]


JAN = 1
FIRST = 1

# There's also a 'gaussian' competition, but I don't participate in that one,
# so leaving it out for now.
SUPPORTED_MONASH_COMPS = ["normal", "info"]

FOOTY_TIPS_FORM_URL = "https://www.footytips.com.au/tipping/afl/"
SPLASH_SERVICE = ""


class MonashSubmitter:
    """Submits tips to one or more of the Monash footy tipping competitions."""

    def __init__(
        self, competitions: Optional[List[str]] = None, browser=None, verbose: int = 1,
    ):
        """
        Instantiate a MonashSubmitter object.

        Params:
        -------
        competitions: Names of the different Monash competitions.
            Based on the option value of the select input for logging into
            a competition.
        browser: Selenium browser for navigating competition websites.
        verbose: How much information to print. 1 prints all messages; 0 prints none.
        """
        self.competitions = competitions or ["normal", "info"]
        self.browser = browser or mechanicalsoup.StatefulBrowser()
        self.verbose = verbose

    def submit_tips(self, predicted_winners: List[PredictedWinner]) -> None:
        """Submit tips to probabilistic-footy.monash.edu.

        Params:
        -------
        predicted_winners: A dict of predicted winners and their predicted results.
        """
        if self.verbose == 1:
            print("Submitting tips to probabilistic-footy.monash.edu...")

        for comp in self.competitions:
            assert comp in SUPPORTED_MONASH_COMPS

            # Need to revisit home page for each competition, because submitting tips
            # doesn't redirect back to it.
            self.browser.open("http://probabilistic-footy.monash.edu/~footy/tips.shtml")
            self._login(comp)
            self._submit_tipping_form(
                self._transform_into_tipping_input(predicted_winners, comp)
            )

            if self.verbose == 1:
                print(f"{comp} tips submitted!")

    def _transform_into_tipping_input(
        self, predicted_winners: List[PredictedWinner], competition
    ) -> Dict[str, str]:
        PREDICTION_TYPE = {"normal": "margin", "info": "win_probability"}
        competition_prediction_type = cast(
            PredictionType, f"predicted_{PREDICTION_TYPE[competition]}",
        )

        return {
            predicted_winner["predicted_winner__name"]: self._clean_numeric_input(
                competition_prediction_type, predicted_winner
            )
            for predicted_winner in predicted_winners
            if predicted_winner[competition_prediction_type] is not None
        }

    @staticmethod
    def _clean_numeric_input(
        competition_prediction_type: PredictionType, predicted_winner: PredictedWinner
    ) -> str:
        prediction_number = predicted_winner[competition_prediction_type]

        # Margin inputs are integers only, so float entries get converted to integers
        # directly instead of rounded (e.g. 5.7 becomes 5)
        if competition_prediction_type == "predicted_margin":
            prediction_number = round(prediction_number)

        # Numeric value inputs are of type "text"
        return str(prediction_number)

    def _login(self, competition: str) -> None:
        login_form = self.browser.select_form()

        login_form.set_input(
            {
                "name": os.environ["MONASH_USERNAME"],
                "passwd": os.environ["MONASH_PASSWORD"],
            }
        )

        login_form.set_select({"comp": competition})
        # There's a round number select, but we don't need to change it,
        # because it defaults to the upcoming/current round on page load.
        self.browser.submit_selected()

        if (
            self.browser.get_current_page().find(text=re.compile("Sorry, the alias"))
            is not None
        ):
            raise ValueError("Tried to use incorrect username and couldn't log in")

        if self.browser.get_current_page().find(text=re.compile("Wrong passwd")):
            raise ValueError("Tried to use incorrect password and couldn't log in")

    def _submit_tipping_form(self, predicted_winners: Dict[str, str]):
        self.browser.select_form()

        # They put the column label row in tbody instead of thead, so we select all
        # rows in the table and subtract 1 from row count to get match count.
        # Also, MechanicalSoup can't find the 'tbody' element for some reason.
        tip_table = self.browser.get_current_page().find("form")
        table_rows = tip_table.find_all("tr")[1:]

        assert len(table_rows) == len(predicted_winners), (
            "The number of predicted winners doesn't match the number of matches. "
            "Check the given predicted winners below:\n"
            f"{predicted_winners}"
        )

        for table_row in table_rows:
            self._enter_prediction(predicted_winners, table_row)

        empty_predictions = [
            input_element.value == "0" or input_element.value == "0.5"
            for input_element in tip_table.select("input[type='text']")
        ]

        assert not any(empty_predictions), (
            f"Found {len(empty_predictions)} empty prediction inputs "
            f"on {self.browser.url}"
        )

        self.browser.submit_selected()

    def _enter_prediction(self, predicted_winners: Dict[str, str], table_row) -> None:
        predicted_winner = None

        # We need to get team names from label text and enter predictions into inputs,
        # so we loop through all of them
        for row_label_or_input in table_row.select("label,input"):
            element_team_name = self._translate_team_name(row_label_or_input.text)

            if element_team_name in predicted_winners.keys():
                team_input = row_label_or_input.find("input")
                self.browser[team_input["name"]] = team_input["value"]
                predicted_winner = element_team_name

            # Have to try/except converting to float, because apparently isnumeric
            # returns False for float strings.
            try:
                float(row_label_or_input.get("value", ""))
            except ValueError:
                continue

            # This is probably a one-off, but as of 2020-06-02,
            # Monash haven't updated their fixture to the post-Covid-break version,
            # so a number of team-match combos don't match the new fixture,
            # resulting in empty predicted winners.
            # There's nothing we can do about it, so we just move on
            # to avoid an error.
            if predicted_winner is None:
                continue

            self.browser[row_label_or_input["name"]] = predicted_winners[
                predicted_winner
            ]

    @staticmethod
    def _translate_team_name(element_text: str) -> str:
        if element_text in TEAM_TRANSLATIONS.keys():
            return TEAM_TRANSLATIONS[element_text]

        return element_text


class FootyTipsSubmitter:
    """Submits tips to the tipping competition on footytips.com.au."""

    def __init__(self, browser=None, verbose: int = 1):
        """
        Instantiate a FootyTipsSubmitter object.

        Params:
        -------
        browser: requests module for posting to the Splash API.
        verbose: How much information to print. 1 prints all messages; 0 prints none.
        """
        self.browser: Any = browser or requests
        self.splash_host = (
            SPLASH_SERVICE
            if os.environ["PYTHON_ENV"] == "production"
            else "http://splash:8050"
        )
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

        predictions = self._transform_into_tipping_input(predicted_winners)
        lua_filepath = os.path.join(
            settings.BASE_DIR, "data", "tipping", "footy_tips_submitter.lua"
        )

        with open(lua_filepath) as lua_file:
            lua_source = "".join(lua_file.readlines())

        response = self.browser.post(
            self.splash_host + "/execute",
            json={
                "lua_source": lua_source,
                # We try to navigate directly to the tipping page, because we will be
                # redirected there once we log in, minimising the number of steps
                "url": FOOTY_TIPS_FORM_URL,
                "username": os.environ["FOOTY_TIPS_USERNAME"],
                "password": os.environ["FOOTY_TIPS_PASSWORD"],
                "predictions": predictions,
                "team_translations": TEAM_TRANSLATIONS,
            },
        )

        if not 200 <= response.status_code < 300:
            if "WARNING" in response.text:
                warn(response.text)
                return None

            raise ValueError(response.text)

        if self.verbose == 1:
            print("Tips submitted!")

    def _transform_into_tipping_input(
        self, predicted_winners: List[PredictedWinner]
    ) -> Dict[str, int]:
        return {
            # We round predicted_margin, because the margin input for footytips
            # only accepts integers.
            self._translate_team_name(
                predicted_winner["predicted_winner__name"]
            ): round(predicted_winner["predicted_margin"])
            for predicted_winner in predicted_winners
            if predicted_winner["predicted_margin"] is not None
        }

    @staticmethod
    def _translate_team_name(element_text: str) -> str:
        if element_text in TEAM_TRANSLATIONS.keys():
            return TEAM_TRANSLATIONS[element_text]

        return element_text


class Tipper:
    """Handles generation and saving of tips (i.e. predictions)."""

    def __init__(  # pylint: disable=dangerous-default-value
        self,
        fetch_data: bool = True,
        data_importer=None,
        ml_models: Optional[List[str]] = None,
        verbose: int = 1,
    ) -> None:
        """
        Instantiate a Tipping object.

        Params:
        -------
        fetch_data: Whether to fetch up-to-date data or load saved data files.
        data_importer: Module used for importing data from remote sources.
        ml_models: A list of names of models to use when making tipping predictions.
        verbose: How much information to print. 1 prints all messages; 0 prints none.
        """
        self.fetch_data = fetch_data
        self.data_importer: Any = data_importer or data_import
        self.ml_models = ml_models

        self._right_now = timezone.localtime()
        self.verbose = verbose

    def fetch_upcoming_fixture(self) -> None:
        """Fetch fixture data and send upcoming match data to the Server API."""
        fixture_data_frame = self._fetch_fixture_data(self._right_now.year)
        upcoming_round, upcoming_matches = self._select_upcoming_matches(
            fixture_data_frame
        )

        if upcoming_round is None or upcoming_matches is None:
            return None

        match_records = upcoming_matches.replace({np.nan: None}).to_dict("records")
        api.update_fixture_data(match_records, upcoming_round)

        return None

    def update_match_predictions(self) -> None:
        """Request prediction data from Augury service for upcoming matches."""
        next_match = api.fetch_next_match()

        if next_match is None:
            if self.verbose == 1:
                print("There are no upcoming matches to predict.")
            return None

        upcoming_round = next_match["round_number"]
        upcoming_season = next_match["season"]

        if self.verbose == 1:
            print(
                "Fetching predictions for round "
                f"{upcoming_round}, {upcoming_season}..."
            )

        prediction_data = self.data_importer.fetch_prediction_data(
            (upcoming_season, upcoming_season + 1),
            round_number=upcoming_round,
            ml_models=self.ml_models,
        )

        if self.verbose == 1:
            print("Predictions received!")

        home_away_df = pivot_team_matches_to_matches(prediction_data)
        predictions = home_away_df.replace({np.nan: None}).to_dict("records")

        api.update_future_match_predictions(predictions)

        return None

    def submit_tips(self, tip_submitters: Optional[List[Any]] = None) -> None:
        """
        Submit tips to the given competitions.

        Params:
        -------
        tip_submitters: List of submitter objects that handle submitting tips
            to competition websites.
        """
        tip_submitters = tip_submitters or [
            MonashSubmitter(verbose=self.verbose),
            # Better to but FootyTipsSubmitter last, because the site has a lot
            # of javascript, and is more prone to errors. They also send an email,
            # so we get confirmation of tips submission.
            FootyTipsSubmitter(verbose=self.verbose),
        ]

        latest_predictions = api.fetch_latest_round_predictions(verbose=self.verbose)

        if not any(latest_predictions):
            if self.verbose == 1:
                print(
                    "No predictions found for the upcoming round. "
                    "Not submitting any tips."
                )

            return None

        for submitter in tip_submitters:
            submitter.verbose = self.verbose
            submitter.submit_tips(latest_predictions)

        return None

    def _fetch_fixture_data(self, year: int) -> pd.DataFrame:
        if self.verbose == 1:
            print(f"Fetching fixture for {year}...\n")

        fixture_data_frame = self.data_importer.fetch_fixture_data(
            start_date=timezone.make_aware(datetime(year, 1, 1)),
            end_date=timezone.make_aware(datetime(year, 12, 31)),
        )

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
