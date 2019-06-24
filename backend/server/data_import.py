"""Module for functions that fetch data"""

from typing import Tuple, Optional, List, Dict, Any, cast
import os
from urllib.parse import urljoin

import pandas as pd
from mypy_extensions import TypedDict
import requests

from server.types import MlModel


DataConfig = TypedDict(
    "DataConfig",
    {"team_names": List[str], "defunct_team_names": List[str], "venues": List[str]},
)


LOCAL_DATA_SCIENCE_SERVICE = "http://data_science:8008"
DATA_SCIENCE_SERVICE = os.getenv(
    "DATA_SCIENCE_SERVICE", default=LOCAL_DATA_SCIENCE_SERVICE
)


def _make_request(url: str, params: Dict[str, Any] = {}) -> requests.Response:
    response = requests.get(url, params=params)

    if response.status_code != 200:
        raise Exception(
            "Bad response from application: "
            f"{response.status_code} / {response.headers} / {response.text}"
        )

    return response


def _fetch_data(path: str, params: Dict[str, Any] = {}) -> List[Dict[str, Any]]:
    service_host = (
        DATA_SCIENCE_SERVICE
        if os.getenv("PYTHON_ENV") == "production"
        else LOCAL_DATA_SCIENCE_SERVICE
    )
    service_url = urljoin(service_host, path)

    response = _make_request(service_url, params)

    return response.json()


def fetch_prediction_data(
    year_range: Tuple[int, int], round_number: Optional[int] = None
) -> pd.DataFrame:
    """
    Fetch prediction data from machine_learning module

    Args:
        year_range (Tuple(int, int)): Min (inclusive) and max (exclusive) years
            for which to fetch data.
        round_number (int): Specify a particular round for which to fetch data.
        verbose (0 or 1): Whether to print info messages while fetching data.

    Returns:
        List of prediction data dictionaries
    """

    min_year, max_year = year_range
    year_range_param = "-".join((str(min_year), str(max_year)))

    return pd.DataFrame(
        _fetch_data(
            "predictions",
            {"year_range": year_range_param, "round_number": round_number},
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

    return pd.DataFrame(
        _fetch_data("fixtures", {"start_date": start_date, "end_date": end_date})
    )


def fetch_match_results_data(start_date: str, end_date: str) -> pd.DataFrame:
    """
    Fetch results data for past matches from machine_learning module.

    Args:
        start_date (str): Stringified date of form yyy-mm-dd that determines
            the earliest date for which to fetch data.
        end_date (str): Stringified date of form yyy-mm-dd that determines
            the latest date for which to fetch data.
        verbose (0 or 1): Whether to print info messages while fetching data.

    Returns:
        pandas.DataFrame with fixture data.
    """

    return pd.DataFrame(
        _fetch_data("match_results", {"start_date": start_date, "end_date": end_date})
    )


def fetch_ml_model_info() -> List[MlModel]:
    """Fetch general info about all saved ML models"""

    return [cast(MlModel, ml_model) for ml_model in _fetch_data("ml_models")]


def fetch_data_config() -> DataConfig:
    """Fetch general data config info"""

    return cast(DataConfig, _fetch_data("data_config"))
