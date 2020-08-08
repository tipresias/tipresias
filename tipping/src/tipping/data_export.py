"""Module for exporting data to the main Tipresias app."""

from typing import Optional, Dict, Any, List
from urllib.parse import urljoin
import json

import pandas as pd
import requests
import simplejson

from tipping.helpers import convert_to_dict
from tipping import settings
from tipping.types import MatchPrediction


def _send_data(path: str, body: Optional[Dict[str, Any]] = None) -> requests.Response:
    body = body or {}

    # I don't feel great about this, but there isn't a good way of converting Numpy
    # data types for JSON. Since requests expects dicts that it converts to JSON for us,
    # we call dumps then loads to avoid nested stringified weirdness.
    stringifiable_body = simplejson.loads(
        simplejson.dumps(body, ignore_nan=True, default=str)
    )

    app_host = settings.TIPRESIAS_APP
    headers = (
        {"Authorization": f"Bearer {settings.TIPRESIAS_APP_TOKEN}"}
        if settings.IS_PRODUCTION
        else {}
    )
    service_url = urljoin(app_host, path)

    response = requests.post(service_url, json=body, headers=headers)

    if 200 <= response.status_code < 300:
        return response

    raise Exception(
        f"Bad response from application when requesting {service_url}:\n"
        f"Status: {response.status_code}\n"
        f"Headers: {response.headers}\n"
        f"Body: {response.text}"
    )


def update_fixture_data(fixture_data: pd.DataFrame, upcoming_round: int):
    """
    POST fixture data to main Tipresias app.

    Params:
    -------
    fixture_data: Data for future matches.
    upcoming_round: Either the current round if ongoing or the next round to be played.
    """
    body = {"upcoming_round": upcoming_round, "data": convert_to_dict(fixture_data)}

    _send_data("/fixtures", body=body)


def update_match_predictions(prediction_data: pd.DataFrame) -> pd.DataFrame:
    """
    POST prediction data to main Tipresias app.

    Params:
    -------
    prediction_data: Predictions from ML models, organised to have one match per row.
    """
    body = {
        "data": convert_to_dict(prediction_data),
    }

    response = _send_data("/predictions", body=body)
    predictions: List[MatchPrediction] = json.loads(response.text)

    return pd.DataFrame(predictions)


def update_matches(match_data: pd.DataFrame):
    """
    POST match data to main Tipresias app.

    Params:
    -------
    match_data: Data from played matches, especially finally scores.
    """
    body = {
        "data": convert_to_dict(match_data),
    }

    _send_data("/matches", body=body)


def update_match_results(match_results_data: pd.DataFrame):
    """
    POST match results data to main Tipresias app.

    Params:
    -------
    match_results_data: Minimal results data from played matches.
    """
    body = {
        "data": convert_to_dict(match_results_data),
    }

    _send_data("/matches", body=body)
