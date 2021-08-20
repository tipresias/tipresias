# pylint: disable=wrong-import-position

"""Serverless functions for fetching and updating application data."""

from typing import List, Union, TypedDict
import json
import os
import sys

import rollbar

SRC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "src")

if SRC_DIR not in sys.path:
    sys.path.append(SRC_DIR)

from tipping import api
from tipping import settings
from tipping.types import CleanPredictionData, MatchData, MLModelInfo


rollbar_token = os.getenv("ROLLBAR_TOKEN", "missing_api_key")
rollbar.init(rollbar_token, settings.ENVIRONMENT)


def rollbar_ignore_handler(payload):
    """Filter out certain errors rom Rollbar logs."""
    error_class_name = (
        payload["data"]
        .get("body", {})
        .get("trace", {})
        .get("exception", {})
        .get("class", "")
    )

    # We ignore ServerErrorResponse, because that error will be recorded in Rollbar
    # by the called service
    if error_class_name == "ServerErrorResponse":
        return False

    return payload


rollbar.events.add_payload_handler(rollbar_ignore_handler)


class Response(TypedDict):
    """Response dict for AWS Lambda functions."""

    statusCode: int
    body: str


def _response(
    data: Union[List[CleanPredictionData], List[MatchData], List[MLModelInfo], str],
    status_code=200,
) -> Response:

    return {"statusCode": status_code, "body": json.dumps({"data": data})}


def _request_is_authorized(http_request) -> bool:
    auth_token = http_request.headers.get("Authorization")

    if settings.IS_PRODUCTION and auth_token != f"Bearer {settings.API_TOKEN}":
        return False

    return True


@rollbar.lambda_function
def update_fixture_data(_event, _context, verbose=1):
    """
    Fetch fixture data and send upcoming match data to the main app.

    verbose: How much information to print. 1 prints all messages; 0 prints none.
    """
    api.update_fixture_data(verbose=verbose)

    return _response("Success")


@rollbar.lambda_function
def update_match_predictions(event, _context, verbose=1):
    """
    Fetch predictions from ML models and send them to the main app.

    verbose: How much information to print. 1 prints all messages; 0 prints none.
    """
    ml_model_names = event.get("ml_model_names")
    api.update_match_predictions(ml_model_names=ml_model_names, verbose=verbose)

    return _response("Success")


@rollbar.lambda_function
def update_matches(_event, _context, verbose=1):
    """
    Fetch match data and send them to the main app.

    verbose: How much information to print. 1 prints all messages; 0 prints none.
    """
    api.update_matches(verbose=verbose)

    return _response("Success")


@rollbar.lambda_function
def update_match_results(_event, _context, verbose=1):
    """
    Fetch match data and send them to the main app.

    verbose: How much information to print. 1 prints all messages; 0 prints none.
    """
    api.update_match_results(verbose=verbose)

    return _response("Success")
