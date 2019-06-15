"""Module for functions that fetch data"""

from typing import List, Tuple, Optional

from server.types import PredictionData
from machine_learning import api


def fetch_prediction_data(
    year_range: Tuple[int, int], round_number: Optional[int] = None, verbose=1
) -> List[PredictionData]:
    """Fetch prediction data from machine_learning module"""

    return api.make_predictions(year_range, round_number=round_number, verbose=verbose)
