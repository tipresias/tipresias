"Module for base class of data importers that use the internal afl_data service"

from typing import Dict, Any, List
import json
from urllib.parse import urljoin

import requests
import pandas as pd

from project.settings.common import MELBOURNE_TIMEZONE

AFL_DATA_SERVICE = "http://afl_data:8001"


class BaseDataImporter:
    def __init__(self, verbose=1):
        self.verbose = verbose

    @staticmethod
    def _fetch_afl_data(path: str, params: Dict[str, Any] = {}) -> List[Dict[str, Any]]:
        data = requests.get(urljoin(AFL_DATA_SERVICE, path), params=params).json()

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
    def _parse_dates(data_frame: pd.DataFrame) -> pd.DataFrame:
        return data_frame.assign(
            date=lambda df: pd.to_datetime(data_frame["date"]).dt.tz_localize(
                MELBOURNE_TIMEZONE
            )
        )
