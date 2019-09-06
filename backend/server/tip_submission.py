"""Module for handling browser automation & submission of tips"""

import os
from datetime import datetime
import re

from splinter import Browser

from project.settings.common import MELBOURNE_TIMEZONE
from server.models import Match, Prediction


JAN = 1
FIRST = 1

# Footytips has some different naming conventions from everyone else,
# so we have to convert a few team names to match how they're displayed on the site
FT_TEAM_TRANSLATIONS = {
    "GWS": "GWS Giants",
    "Brisbane": "Brisbane Lions",
    "West Coast": "West Coast Eagles",
}


def _translate_team_name(team_name):
    if team_name not in FT_TEAM_TRANSLATIONS:
        return team_name

    return FT_TEAM_TRANSLATIONS[team_name]


def _get_predicted_winners(prediction_values):
    return [
        _translate_team_name(pred.get("predicted_winner__name"))
        for pred in prediction_values
    ]


def submit_tips():
    latest_match = Match.objects.latest("start_date_time")
    latest_year = latest_match.start_date_time.year
    latest_round = latest_match.round_number

    latest_round_predictions = (
        Prediction.objects.filter(
            ml_model__name="tipresias",
            match__start_date_time__gt=datetime(
                latest_year, JAN, FIRST, tzinfo=MELBOURNE_TIMEZONE
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

    predicted_winners = _get_predicted_winners(latest_round_predictions)
    predicted_winners_regex = re.compile(f"{'|'.join(predicted_winners)}")

    browser = Browser("firefox", headless=True)
    browser.visit("https://www.footytips.com.au/tipping/afl/")

    # Have to use second login form, because the first is some invisible Angular
    # something something
    login_form = browser.find_by_name("frmLogin")[1]
    login_form.find_by_name("userLogin").fill(os.getenv("FOOTY_TIPS_USERNAME", ""))
    login_form.find_by_name("userPassword").fill(os.getenv("FOOTY_TIPS_PASSWORD", ""))
    login_form.find_by_id("signin-ft").click()

    team_matches = browser.find_by_css(".tip-selection")

    for team_match in team_matches:
        team_match_input = team_match.find_by_css(".radio-button")

        if (
            predicted_winners_regex.search(team_match.text) is not None
            and team_match_input.visible
        ):
            team_match_input.click()

    browser.find_by_css(".tipform-submit-button").first.click()
