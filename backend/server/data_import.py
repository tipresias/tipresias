"""Module for functions that fetch data"""

from typing import Tuple, Optional, List, Dict, Any, cast
import os
from urllib.parse import urljoin
from dateutil import parser

import pandas as pd
import requests

from server.types import MlModel


LOCAL_DATA_SCIENCE_SERVICE = "http://data_science:8008"
DATA_SCIENCE_SERVICE = os.getenv(
    "DATA_SCIENCE_SERVICE", default=LOCAL_DATA_SCIENCE_SERVICE
)


def _parse_dates(data_frame: pd.DataFrame) -> pd.Series:
    # We have to use dateutil.parser instead of a pandas datetime parser,
    # because the former doesn't maintain the timezone offset.
    # We make sure all datetimes are converted to UTC, because that makes things
    # easier due to Django converting all datetime fields to UTC when saving DB records.
    return data_frame["date"].map(lambda dt: parser.parse(dt).astimezone(pytz.UTC))


def _make_request(
    url: str, params: Dict[str, Any] = {}, headers: Dict[str, str] = {}
) -> requests.Response:
    response = requests.get(url, params=params, headers=headers)

    if response.status_code != 200:
        raise Exception(
            "Bad response from application: "
            f"{response.status_code} / {response.headers} / {response.text}"
        )

    return response


def _fetch_data(path: str, params: Dict[str, Any] = {}) -> List[Dict[str, Any]]:
    if os.getenv("PYTHON_ENV") == "production":
        service_host = DATA_SCIENCE_SERVICE
        headers = {"Authorization": f'Bearer {os.getenv("GCPF_TOKEN")}'}
    else:
        service_host = LOCAL_DATA_SCIENCE_SERVICE
        headers = {}

    service_url = urljoin(service_host, path)

    response = _make_request(service_url, params=params, headers=headers)

    return response.json().get("data")


def fetch_prediction_data(
    year_range: Tuple[int, int],
    round_number: Optional[int] = None,
    ml_models: str = None,
) -> pd.DataFrame:
    """
    Fetch prediction data from machine_learning module

    Args:
        year_range (Tuple(int, int)): Min (inclusive) and max (exclusive) years
            for which to fetch data.
        round_number (int): Specify a particular round for which to fetch data.
        ml_models (str): Comma-separated list of ML model names to use for making
            predictions.
        verbose (0 or 1): Whether to print info messages while fetching data.

    Returns:
        List of prediction data dictionaries
    """

    min_year, max_year = year_range
    year_range_param = "-".join((str(min_year), str(max_year)))

    return pd.DataFrame(
        _fetch_data(
            "predictions",
            {
                "year_range": year_range_param,
                "round_number": round_number,
                "ml_models": ml_models,
            },
        )
    )


def fetch_fixture_data(start_date: str, end_date: str) -> pd.DataFrame:
    """
    Fetch fixture data (doesn't include match results) from machine_learning module.

    Args:
        start_date (str): Stringified date of form yyy-mm-dd that determines
            the earliest date for which to fetch data.
        end_date (str): Stringified date of form yyy-mm-dd that determines
            the latest date for which to fetch data.
        verbose (0 or 1): Whether to print info messages while fetching data.

    Returns:
        pandas.DataFrame with fixture data.
    """

    fixtures = pd.DataFrame(
        _fetch_data("fixtures", {"start_date": start_date, "end_date": end_date})
    )

    if fixtures.any().any():
        return fixtures.assign(date=_parse_dates)

    return fixtures


def fetch_match_results_data(
    start_date: str, end_date: str, fetch_data: bool = False
) -> pd.DataFrame:
    """
    Fetch results data for past matches from machine_learning module.

    Args:
        start_date (str): Stringified date of form yyy-mm-dd that determines
            the earliest date for which to fetch data.
        end_date (str): Stringified date of form yyy-mm-dd that determines
            the latest date for which to fetch data.
        fetch_data (bool): Whether to fetch fresh data. Non-fresh data goes up to end
            of 2016 season.

    Returns:
        pandas.DataFrame with fixture data.
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
    """Fetch general info about all saved ML models"""

    return [cast(MlModel, ml_model) for ml_model in _fetch_data("ml_models")]
