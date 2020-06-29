"""Module for exporting data to the main Tipresias app."""

import numpy as np
import pandas as pd
import requests

from tipping import settings


def update_fixture_data(fixture_data: pd.DataFrame, upcoming_round: int):
    """
    POST fixture data to main Tipresias app.

    Params:
    -------
    fixture_data: Data for future matches.
    upcoming_round: Either the current round if ongoing or the next round to be played.
    """
    url = settings.TIPRESIAS_APP + "/fixtures"
    body = {
        "upcoming_round": upcoming_round,
        "data": fixture_data.replace({np.nan: None}).to_dict("records"),
    }

    response = requests.post(url, json=body)

    if 200 <= response.status_code < 300:
        return None

    raise Exception(
        f"Bad response from application when posting to {url}:\n"
        f"Status: {response.status_code}\n"
        f"Headers: {response.headers}\n"
        f"Body: {response.text}"
    )


def update_match_predictions(prediction_data: pd.DataFrame):
    """
    POST prediction data to main Tipresias app.

    Params:
    -------
    prediction_data: Predictions from ML models, organised to have one match per row.
    """
    url = settings.TIPRESIAS_APP + "/predictions"
    body = {
        "data": prediction_data.replace({np.nan: None}).to_dict("records"),
    }

    response = requests.post(url, json=body)

    if 200 <= response.status_code < 300:
        return None

    raise Exception(
        f"Bad response from application when posting to {url}:\n"
        f"Status: {response.status_code}\n"
        f"Headers: {response.headers}\n"
        f"Body: {response.text}"
    )
