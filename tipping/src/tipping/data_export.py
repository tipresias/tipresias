"""Module for exporting data to the main Tipresias app."""

from typing import Optional, Dict, Any, List
from urllib.parse import urljoin

import numpy as np
import pandas as pd
import requests

from tipping import settings


IS_PRODUCTION = settings.ENVIRONMENT == "production"


def _send_data(path: str, body: Optional[Dict[str, Any]] = None) -> None:
    body = body or {}

    app_host = settings.TIPRESIAS_APP
    headers = (
        {"Authorization": f"Bearer {settings.TIPRESIAS_APP_TOKEN}"}
        if IS_PRODUCTION
        else {}
    )

    service_url = urljoin(app_host, path)

    response = requests.post(service_url, json=body, headers=headers)

    if 200 <= response.status_code < 300:
        return None

    raise Exception(
        f"Bad response from application when requesting {service_url}:\n"
        f"Status: {response.status_code}\n"
        f"Headers: {response.headers}\n"
        f"Body: {response.text}"
    )


def _convert_to_dict(data_frame: pd.DataFrame) -> List[Dict[str, Any]]:
    type_conversion = {"date": str} if "date" in data_frame.columns else {}
    return data_frame.replace({np.nan: None}).astype(type_conversion).to_dict("records")


def update_fixture_data(fixture_data: pd.DataFrame, upcoming_round: int):
    """
    POST fixture data to main Tipresias app.

    Params:
    -------
    fixture_data: Data for future matches.
    upcoming_round: Either the current round if ongoing or the next round to be played.
    """
    body = {"upcoming_round": upcoming_round, "data": _convert_to_dict(fixture_data)}

    _send_data("/fixtures", body=body)


def update_match_predictions(prediction_data: pd.DataFrame):
    """
    POST prediction data to main Tipresias app.

    Params:
    -------
    prediction_data: Predictions from ML models, organised to have one match per row.
    """
    body = {
        "data": _convert_to_dict(prediction_data),
    }

    _send_data("/predictions", body=body)


def update_match_results(match_data: pd.DataFrame):
    """
    POST match data to main Tipresias app.

    Params:
    -------
    match_data: Data from played matches, especially finally scores.
    """
    url = settings.TIPRESIAS_APP + "/matches"
    body = {
        "data": _convert_to_dict(match_data),
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
