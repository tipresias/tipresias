"""View methods for rendering HTTP responses."""

import json

from django.http import HttpRequest, HttpResponse
from django.conf import settings
import numpy as np
import pandas as pd

from server.helpers import pivot_team_matches_to_matches
from server.models import Prediction
from server.tipping import Tipper


def predictions(request: HttpRequest):
    """Handle POST request to /predictions with prediction data in the body."""
    if request.method != "POST":
        return HttpResponse(status=405)

    authorization = request.headers.get("Authorization")
    if (
        settings.ENVIRONMENT == "production"
        and authorization != f"Bearer {settings.API_TOKEN}"
    ):
        return HttpResponse(status=401)

    body = json.loads(request.body)
    prediction_data = pd.DataFrame(body["data"])

    home_away_df = pivot_team_matches_to_matches(prediction_data)

    for pred in home_away_df.replace({np.nan: None}).to_dict("records"):
        Prediction.update_or_create_from_raw_data(pred)

    Tipper().submit_tips()

    return HttpResponse(status=200)
