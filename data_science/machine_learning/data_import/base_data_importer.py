"Module for base class of data importers that use the internal afl_data service"

from typing import Dict, Any, List
import json
from urllib.parse import urljoin
import os

import requests
import pandas as pd

from machine_learning.settings import MELBOURNE_TIMEZONE


LOCAL_AFL_DATA_SERVICE = "http://afl_data:8080"
AFL_DATA_SERVICE = os.getenv("AFL_DATA_SERVICE", default=LOCAL_AFL_DATA_SERVICE)


class BaseDataImporter:
    def __init__(self, verbose=1):
        self.verbose = verbose

    def _fetch_afl_data(
        self, path: str, params: Dict[str, Any] = {}
    ) -> List[Dict[str, Any]]:
        service_host = (
            AFL_DATA_SERVICE
            if os.getenv("PYTHON_ENV") == "production"
            else LOCAL_AFL_DATA_SERVICE
        )
        service_url = urljoin(service_host, path)

        response = self._make_request(service_url, params)

        return self._handle_response_data(response)

    @staticmethod
    def _make_request(url: str, params: Dict[str, Any] = {}) -> requests.Response:
        response = requests.get(url, params=params)

        if response.status_code != 200:
            raise Exception(
                "Bad response from application: "
                f"{response.status_code} / {response.headers} / {response.text}"
            )

        return response

    @staticmethod
    def _handle_response_data(response: requests.Response) -> List[Dict[str, Any]]:
        data = response.json()

        if isinstance(data, dict) and "error" in data.keys():
            raise RuntimeError(data["error"])

        if len(data) == 1:
            # For some reason, when returning match data with fetch_data=False,
            # plumber returns JSON as a big string inside a list, so we have to parse
            # the first element
            return json.loads(data[0])

        if any(data):
            return data

        return []

    @staticmethod
    def _parse_dates(data_frame: pd.DataFrame) -> pd.Series:
        return pd.to_datetime(data_frame["date"]).dt.tz_localize(MELBOURNE_TIMEZONE)
