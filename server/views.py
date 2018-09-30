import os
import sys
import pandas as pd
from django.http import JsonResponse

PROJECT_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '../')
)

if PROJECT_PATH not in sys.path:
    sys.path.append(PROJECT_PATH)


def predictions(request):  # pylint: disable=W0613
    """Render JSON data of model predictions"""

    data_frame = pd.read_csv(f'{PROJECT_PATH}/data/model_predictions.csv')
    data = {'data': data_frame.to_dict('records')}

    return JsonResponse(data)
