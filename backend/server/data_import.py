"""Module for functions that fetch data"""

from typing import List

from server.types import PredictionData
from machine_learning import api


def fetch_prediction_data(year: int, round_number: int) -> List[PredictionData]:
    """Fetch prediction data from machine_learning module"""

    return api.make_predictions(year, round_number=round_number)
