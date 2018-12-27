"""Module for server views"""

import pandas as pd
from django.http import JsonResponse, HttpRequest

from project.settings.common import DATA_DIR


def predictions(request: HttpRequest) -> JsonResponse:  # pylint: disable=W0613
    """Render JSON data of model predictions"""

    data_frame = pd.read_csv(f"{DATA_DIR}/model_predictions.csv")
    data = {"data": data_frame.to_dict("records")}

    return JsonResponse(data)
