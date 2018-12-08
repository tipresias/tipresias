import os
import sys
import pandas as pd
from django.http import JsonResponse, HttpRequest

from project.settings.common import BASE_DIR


def predictions(request: HttpRequest) -> JsonResponse:  # pylint: disable=W0613
    """Render JSON data of model predictions"""

    data_frame = pd.read_csv(f"{BASE_DIR}/data/model_predictions.csv")
    data = {"data": data_frame.to_dict("records")}

    return JsonResponse(data)
