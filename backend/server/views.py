"""View methods for rendering HTTP responses."""

from typing import cast, List
import json
import pytz
from dateutil import parser

from django.http import HttpRequest, HttpResponse
from django.conf import settings

from server import api
from server.types import FixtureData, MatchData


def predictions(request: HttpRequest, verbose=1):
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

    api.update_future_match_predictions(prediction_data)
    prediction_records = list(api.fetch_latest_round_predictions(verbose=verbose))

    return HttpResponse(
        content=json.dumps(prediction_records),
        content_type="application/json",
        status=200,
    )


def fixtures(request: HttpRequest, verbose=1):
    """Handle POST request to /fixtures with fixture data in the body."""
    if request.method != "POST":
        return HttpResponse(status=405)

    authorization = request.headers.get("Authorization")
    if (
        settings.ENVIRONMENT == "production"
        and authorization != f"Bearer {settings.API_TOKEN}"
    ):
        return HttpResponse(status=401)

    body = json.loads(request.body)
    fixture_data = [
        {**match, **{"date": parser.parse(match["date"]).replace(tzinfo=pytz.UTC)}}
        for match in body["data"]
    ]
    upcoming_round = body["upcoming_round"]

    api.update_fixture_data(
        cast(List[FixtureData], fixture_data), upcoming_round, verbose=verbose
    )

    return HttpResponse("Success", content_type="application/json", status=200)


def matches(request: HttpRequest, verbose=1):
    """Handle POST request to /matches with match data in the body."""
    if request.method != "POST":
        return HttpResponse(status=405)

    authorization = request.headers.get("Authorization")
    if (
        settings.ENVIRONMENT == "production"
        and authorization != f"Bearer {settings.API_TOKEN}"
    ):
        return HttpResponse(status=401)

    body = json.loads(request.body)
    match_data = [
        {**match, **{"date": parser.parse(match["date"]).replace(tzinfo=pytz.UTC)}}
        for match in body["data"]
    ]

    api.backfill_recent_match_results(
        cast(List[MatchData], match_data), verbose=verbose
    )

    return HttpResponse("Success", content_type="application/json", status=200)
