"""Module for functions that fetch data."""

from typing import Tuple, Optional, List, Dict, Any, cast, Union
import os
from datetime import datetime
from urllib.parse import urljoin
from dateutil import parser
import pytz

import pandas as pd
import requests
from django.utils import timezone

from server.types import MlModel

ParamValue = Union[str, int, datetime]

DATA_SCIENCE_SERVICE = os.environ["DATA_SCIENCE_SERVICE"]


def _parse_dates(data_frame: pd.DataFrame) -> pd.Series:
    # We have to use dateutil.parser instead of a pandas datetime parser,
    # because the former doesn't maintain the timezone offset.
    # We make sure all datetimes are converted to UTC, because that makes things
    # easier due to Django converting all datetime fields to UTC when saving DB records.
    return data_frame["date"].map(lambda dt: timezone.localtime(parser.parse(dt)))


def _make_request(
    url: str,
    params: Optional[Dict[str, Any]] = None,
    headers: Optional[Dict[str, str]] = None,
) -> requests.Response:
    params = params or {}
    headers = headers or {}

    response = requests.get(url, params=params, headers=headers)

    if response.status_code != 200:
        raise Exception(
            f"Bad response from application when requesting {url}:\n"
            f"Status: {response.status_code}\n"
            f"Headers: {response.headers}\n"
            f"Body: {response.text}"
        )

    return response


def _clean_datetime_param(param_value: ParamValue) -> Optional[str]:
    if not isinstance(param_value, datetime):
        return None

    # For the edge-case in which this gets run early enough in the morning
    # such that UTC is still the previous day, and the start/end date filters are all
    # one day off.
    return str(
        timezone.localtime(
            param_value, timezone=pytz.timezone("Australia/Melbourne")
        ).date()
    )


def _clean_param_value(param_value: ParamValue) -> str:
    return _clean_datetime_param(param_value) or str(param_value)


def _fetch_data(
    path: str, params: Optional[Dict[str, Any]] = None
) -> List[Dict[str, Any]]:
    params = params or {}

    service_host = DATA_SCIENCE_SERVICE
    headers = {"Authorization": f'Bearer {os.environ["GCPF_TOKEN"]}'}

    service_url = urljoin(service_host, path)
    clean_params = {
        key: _clean_param_value(value)
        for key, value in params.items()
        if value is not None
    }

    response = _make_request(service_url, params=clean_params, headers=headers)

    return response.json().get("data")


def fetch_prediction_data(
    year_range: Tuple[int, int],
    round_number: Optional[int] = None,
    ml_models: Optional[List[str]] = None,
    train_models: Optional[bool] = False,
) -> pd.DataFrame:
    """
    Fetch prediction data from machine_learning module.

    Params:
    -------
    year_range: Min (inclusive) and max (exclusive) years for which to fetch data.
    round_number: Specify a particular round for which to fetch data.
    ml_models: List of ML model names to use for making predictions.

    Returns:
    --------
        List of prediction data dictionaries.
    """
    min_year, max_year = year_range
    year_range_param = "-".join((str(min_year), str(max_year)))
    ml_model_param = None if ml_models is None else ",".join(ml_models)

    return pd.DataFrame(
        _fetch_data(
            "predictions",
            {
                "year_range": year_range_param,
                "round_number": round_number,
                "ml_models": ml_model_param,
                "train_models": train_models,
            },
        )
    )


def fetch_fixture_data(start_date: datetime, end_date: datetime) -> pd.DataFrame:
    """
    Fetch fixture data (doesn't include match results) from machine_learning module.

    Params:
    -------
    start_date: Timezone-aware date-time that determines the earliest date
        for which to fetch data.
    end_date: Timezone-aware date-time that determines the latest date
        for which to fetch data.

    Returns:
    --------
        pandas.DataFrame with fixture data.
    """
    fixtures = pd.DataFrame(
        _fetch_data("fixtures", {"start_date": start_date, "end_date": end_date})
    )

    if fixtures.any().any():
        return fixtures.assign(date=_parse_dates)

    return fixtures


def fetch_match_results_data(
    start_date: datetime, end_date: datetime, fetch_data: bool = False
) -> pd.DataFrame:
    """
    Fetch results data for past matches from machine_learning module.

    Params:
    -------
    start_date: Timezone-aware date-time that determines the earliest date
        for which to fetch data.
    end_date: Timezone-aware date-time that determines the latest date
        for which to fetch data.
    fetch_data: Whether to fetch fresh data. Non-fresh data goes up to end
        of 2016 season.

    Returns:
    --------
        pandas.DataFrame with match results data.
    """
    match_results = pd.DataFrame(
        _fetch_data(
            "match_results",
            {"start_date": start_date, "end_date": end_date, "fetch_data": fetch_data},
        )
    )

    if any(match_results):
        return match_results.assign(date=_parse_dates)

    return match_results


def fetch_ml_model_info() -> List[MlModel]:
    """
    Fetch general info about all saved ML models.

    Returns:
    --------
    A list of objects with basic info about each ML model.
    """
    return [cast(MlModel, ml_model) for ml_model in _fetch_data("ml_models")]
