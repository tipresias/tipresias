"""Module for handling generation and saving of tips (i.e. predictions)."""

from typing import List, Optional, Dict, Union, Literal, cast, Any
import os
from warnings import warn
import re

import pandas as pd
import mechanicalsoup
import requests

from tipping import settings
from tipping.helpers import convert_to_dict
from tipping.types import MatchPrediction


PredictionType = Union[
    Literal["predicted_margin"], Literal["predicted_win_probability"]
]


JAN = 1
FIRST = 1
DEC = 12
THIRTY_FIRST = 31

# There's also a 'gaussian' competition, but I don't participate in that one,
# so leaving it out for now.
SUPPORTED_MONASH_COMPS = ["normal", "info"]

FOOTY_TIPS_FORM_URL = "https://www.footytips.com.au/tipping/afl/"


class MonashSubmitter:
    """Submits tips to one or more of the Monash footy tipping competitions."""

    def __init__(
        self, competitions: Optional[List[str]] = None, browser=None, verbose: int = 1
    ):
        """
        Instantiate a MonashSubmitter object.

        Params:
        -------
        competitions: Names of the different Monash competitions.
            Based on the option value of the select input for logging into
            a competition.
        browser: MechanicalSoup stateful browser for navigating competition websites.
        verbose: How much information to print. 1 prints all messages; 0 prints none.
        """
        self.competitions = competitions or ["normal", "info"]
        self.browser = browser or mechanicalsoup.StatefulBrowser()
        self.verbose = verbose

    def submit_tips(self, predictions: pd.DataFrame) -> None:
        """Submit tips to probabilistic-footy.monash.edu.

        Params:
        -------
        predictions: Predicted winners and their predicted results.
        """
        if self.verbose == 1:
            print("Submitting tips to probabilistic-footy.monash.edu...")

        for comp in self.competitions:
            predicted_winners = self._transform_into_tipping_input(comp, predictions)
            self._submit_competition_tips(comp, predicted_winners)

            if self.verbose == 1:
                print(f"{comp} tips submitted!")

    def _transform_into_tipping_input(
        self, competition: str, predictions: pd.DataFrame
    ) -> Dict[str, str]:
        PREDICTION_TYPE = {"normal": "margin", "info": "win_probability"}
        competition_prediction_type = cast(
            PredictionType, f"predicted_{PREDICTION_TYPE[competition]}"
        )
        predicted_winners = cast(List[MatchPrediction], convert_to_dict(predictions))

        return {
            predicted_winner["predicted_winner__name"]: self._clean_numeric_input(
                competition_prediction_type, predicted_winner
            )
            for predicted_winner in predicted_winners
            if predicted_winner[competition_prediction_type] is not None
        }

    @staticmethod
    def _clean_numeric_input(
        competition_prediction_type: PredictionType, predicted_winner: MatchPrediction
    ) -> str:
        prediction_number = predicted_winner[competition_prediction_type]

        # Margin inputs are integers only, so float entries get converted to integers
        # directly instead of rounded (e.g. 5.7 becomes 5)
        if competition_prediction_type == "predicted_margin":
            prediction_number = round(prediction_number)

        # Numeric value inputs are of type "text"
        return str(prediction_number)

    def _submit_competition_tips(
        self, competition: str, predicted_winners: Dict[str, str]
    ):
        assert competition in SUPPORTED_MONASH_COMPS

        # Need to revisit home page for each competition, because submitting tips
        # doesn't redirect back to it.
        self.browser.open("http://probabilistic-footy.monash.edu/~footy/tips.shtml")
        self._login(competition)
        self._submit_tipping_form(predicted_winners)

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
        if element_text in settings.TEAM_TRANSLATIONS.keys():
            return settings.TEAM_TRANSLATIONS[element_text]

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
            os.environ["SPLASH_SERVICE"]
            if settings.ENVIRONMENT == "production"
            else "http://splash:8050"
        )
        self.verbose = verbose

    def submit_tips(self, predictions: pd.DataFrame) -> None:
        """
        Submit tips to footytips.com.au.

        Params:
        -------
        predicted_winners: A dict where the keys are team names and the values
            are their predicted margins. Only includes predicted winners.
        """
        if self.verbose == 1:
            print("Submitting tips to footytips.com.au...")

        predicted_winners = self._transform_into_tipping_input(predictions)
        response = self._call_splash_service(predicted_winners)

        if not 200 <= response.status_code < 300:
            if "WARNING" in response.text:
                warn(response.text)
                return None

            raise ValueError(response.text)

        if self.verbose == 1:
            print("Tips submitted!")

    def _transform_into_tipping_input(
        self, predictions: pd.DataFrame
    ) -> Dict[str, int]:
        predicted_winners = cast(List[MatchPrediction], convert_to_dict(predictions))

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
        if element_text in settings.TEAM_TRANSLATIONS.keys():
            return settings.TEAM_TRANSLATIONS[element_text]

        return element_text

    def _call_splash_service(self, predictions: Dict[str, int]) -> requests.Response:
        lua_filepath = os.path.join(
            settings.SRC_DIR, "tipping", "footy_tips_submitter.lua"
        )

        with open(lua_filepath) as lua_file:
            lua_source = "".join(lua_file.readlines())

        return self.browser.post(
            self.splash_host + "/execute",
            json={
                "lua_source": lua_source,
                # We try to navigate directly to the tipping page, because we will be
                # redirected there once we log in, minimising the number of steps
                "url": FOOTY_TIPS_FORM_URL,
                "username": os.environ["FOOTY_TIPS_USERNAME"],
                "password": os.environ["FOOTY_TIPS_PASSWORD"],
                "predictions": predictions,
                "team_translations": settings.TEAM_TRANSLATIONS,
            },
        )
