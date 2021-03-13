"""Module for functions that fetch data."""

from typing import Optional, List, Dict, Any, cast, Union
from urllib.parse import urljoin
from datetime import datetime
import re
from dateutil import parser
import pytz

import pandas as pd
import requests
from mypy_extensions import TypedDict

from tipping import settings
from tipping.types import MLModelInfo


ParamValue = Union[str, int, datetime]
PredictionData = TypedDict(
    "PredictionData",
    {"ml_models": List[str], "round_number": int, "year_range": List[int]},
)


DATE_STRING_REGEX = re.compile(r"^\d{4}\-\d{2}\-\d{2}$")


class DataImportError(Exception):
    """Base error class for data_import."""


class ServerErrorResponse(DataImportError):
    """Error class for when a server error response is received."""


class DataImporter:
    """Imports data from the data science service."""

    def __init__(self, client=requests):
        """Instantiate a DataImporter object.

        Params:
        -------
        client: HTTP client for calling external APIs.
        """
        self.client = client

    def fetch_prediction_data(
        self,
        year_range: str,
        round_number: Optional[int] = None,
        ml_model_names: Optional[str] = None,
        train_models: Optional[bool] = False,
    ) -> pd.DataFrame:
        """
        Fetch prediction data from ML models in the data-science service.

        Params:
        -------
        year_range: Min (inclusive) and max (exclusive) years for which to fetch data.
            Format is 'yyyy-yyyy'.
        round_number: Specify a particular round for which to fetch data.
        ml_model_names: Comma-separated string of ML model names to use
            for making predictions.
        train_models: Whether to train models in between predictions (only applies
            when predicting across multiple seasons).

        Returns:
        --------
        Predictions data frame.
        """
        prediction_data = self._fetch_data(
            "predictions",
            {
                "year_range": year_range,
                "round_number": round_number,
                "ml_models": ml_model_names or None,
                "train_models": train_models,
            },
        )

        return pd.DataFrame(prediction_data)

    def fetch_fixture_data(
        self, start_date: datetime, end_date: datetime
    ) -> pd.DataFrame:
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
            data=self._fetch_data(
                "fixtures", {"start_date": start_date, "end_date": end_date}
            )
        )

        if fixtures.any().any():
            return fixtures.assign(date=self._parse_dates)

        return fixtures

    def fetch_match_data(
        self, start_date: str, end_date: str, fetch_data: bool = False
    ) -> pd.DataFrame:
        """
        Fetch data for past matches from machine_learning module.

        Params:
        -------
        start_date: Date string that determines the earliest date
            for which to fetch data. Format is 'yyyy-mm-dd'.
        end_date: Date string that determines the latest date
            for which to fetch data. Format is 'yyyy-mm-dd'.
        fetch_data: Whether to fetch fresh data. Non-fresh data goes up to end
            of previous season.

        Returns:
        --------
        pandas.DataFrame with match data.
        """
        self._validate_date_string(start_date)
        self._validate_date_string(end_date)
        matches = pd.DataFrame(
            self._fetch_data(
                "matches",
                {
                    "start_date": start_date,
                    "end_date": end_date,
                    "fetch_data": fetch_data,
                },
            )
        )

        if any(matches):
            return matches.assign(date=self._parse_dates)

        return matches

    def fetch_match_results_data(self, round_number: int) -> pd.DataFrame:
        """
        Fetch minimal match results data.

        Params:
        -------
        round_number: Fetch results for the given round.

        Returns:
        --------
        pandas.DataFrame with match data.
        """
        match_results = pd.DataFrame(
            self._fetch_data("match_results", {"round_number": round_number})
        )

        if any(match_results):
            return match_results.assign(date=self._parse_dates)

        return match_results

    def fetch_ml_model_info(self) -> pd.DataFrame:
        """
        Fetch general info about all saved ML models.

        Returns:
        --------
        A list of objects with basic info about each ML model.
        """
        return pd.DataFrame(
            [cast(MLModelInfo, ml_model) for ml_model in self._fetch_data("ml_models")]
        )

    @staticmethod
    def _validate_date_string(date_string: str):
        assert (
            DATE_STRING_REGEX.match(date_string) is not None
        ), f"Date strings must have format yyyy-mm-dd. Received {date_string}"

    @staticmethod
    def _parse_dates(data_frame: pd.DataFrame) -> pd.Series:
        # We have to use dateutil.parser instead of a pandas datetime parser,
        # because the former doesn't maintain the timezone offset.
        # We make sure all datetimes are converted to UTC, because that makes things
        # easier due to Django converting all datetime fields to UTC when saving DB records.
        return data_frame["date"].map(
            lambda dt: parser.parse(dt).replace(tzinfo=pytz.UTC)
        )

    @staticmethod
    def _clean_datetime_param(param_value: ParamValue) -> Optional[str]:
        if not isinstance(param_value, datetime):
            return None

        # For the edge-case in which this gets run early enough in the morning
        # such that UTC is still the previous day, and the start/end date filters are all
        # one day off.
        return str(param_value.astimezone(pytz.timezone("Australia/Melbourne")).date())

    def _clean_param_value(self, param_value: ParamValue) -> str:
        return self._clean_datetime_param(param_value) or str(param_value)

    def _fetch_data(
        self, path: str, params: Optional[Dict[str, Any]] = None
    ) -> Union[List[Dict[str, Any]], PredictionData]:
        params = params or {}

        service_host = settings.DATA_SCIENCE_SERVICE
        headers = (
            {"Authorization": f"Bearer {settings.DATA_SCIENCE_SERVICE_TOKEN}"}
            if settings.IS_PRODUCTION
            else {}
        )

        service_url = urljoin(service_host, path)
        clean_params = {
            key: self._clean_param_value(value)
            for key, value in params.items()
            if value is not None
        }

        response = requests.get(service_url, params=clean_params, headers=headers)

        if 200 <= response.status_code < 300:
            return response.json().get("data")

        if 500 <= response.status_code < 600:
            raise ServerErrorResponse(self._error_message(service_url, response))

        raise DataImportError(service_url, self._error_message(service_url, response))

    @staticmethod
    def _error_message(url: str, response: requests.Response) -> str:
        return (
            f"Bad response from application when requesting {url}:\n"
            f"Status: {response.status_code}\n"
            f"Headers: {response.headers}\n"
            f"Body: {response.text}"
        )
