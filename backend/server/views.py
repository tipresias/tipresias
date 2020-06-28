"""View methods for rendering HTTP responses."""

import json

from django.http import HttpRequest, HttpResponse
from django.conf import settings

from server.models import Prediction


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
    prediction_data = body["data"]

    for pred in prediction_data:
        Prediction.update_or_create_from_raw_data(pred)

    return HttpResponse("Success", status=200)
