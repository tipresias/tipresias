import os
import sys
import json
import pandas as pd

PROJECT_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '../../../')
)

if PROJECT_PATH not in sys.path:
    sys.path.append(PROJECT_PATH)


class ApiController:
    """Base controller for API calls"""

    def predictions(self):  # pylint: disable=R0201
        """Render JSON data of model predictions"""

        data_frame = pd.read_csv(f'{PROJECT_PATH}/data/model_predictions.csv')
        return json.dumps(data_frame.to_dict('records'))
