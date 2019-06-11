"""Module for functions that fetch data"""

from typing import List
import os

import requests

from server.types import Prediction


def fetch_predictions(year: int, round_number: int) -> List[Prediction]:
    """Fetch prediction data from machine_learning service"""

    response = requests.get(
        os.environ.get("ML_SERVICE", default=""),
        params={"year": year, "round_number": round_number},
        headers={"Authorization": os.environ.get("GCPF_TOKEN")},
    )

    if response.status_code != 200:
        response.raise_for_status()

    return response.json()
