"""Serverless functions for fetching and updating application data."""

from typing import List, Dict, Any, Union, TypedDict
import json
import os
import sys

SRC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "src")

if SRC_DIR not in sys.path:
    sys.path.append(SRC_DIR)

from tipping import api  # pylint: disable=wrong-import-position


class Response(TypedDict):
    """Response dict for AWS Lambda functions."""

    statusCode: int
    body: str


def _response(data: Union[List[Dict[str, Any]], Dict[str, Any]]) -> Response:
    return {"statusCode": 200, "body": json.dumps(data)}


def hello(event, _context) -> Response:
    """Say hello."""
    body = {
        "message": "Go Serverless v1.0! Your function executed successfully!",
        "input": event,
    }

    return _response(body)

    # Use this code if you don't use the http event with the LAMBDA-PROXY
    # integration
    # """
    # return {
    #     "message": "Go Serverless v1.0! Your function executed successfully!",
    #     "event": event
    # }
    # """


def fetch_match_predictions(event, _context):
    """
    Get match predictions from ML models.

    Params:
    -------
    event: AWS Lambda event dict with the following params:
        year_range: Min (inclusive) and max (exclusive) years for which to fetch data.
            Format is 'yyyy-yyyy'.
        round_number: Specify a particular round for which to fetch data.
        ml_models: List of ML model names to use for making predictions.
        train_models: Whether to train models in between predictions (only applies
            when predicting across multiple seasons).

    Returns:
    --------
    List of prediction data dictionaries in a JSON body.
    """
    VALID_KWARGS = ["round_number", "ml_models", "train_models"]
    year_range = event["year_range"]

    year_range_values = year_range.split("-")
    assert len(set(year_range_values)) == 2, (
        "year_range param must have two non-equal years. "
        f"Instead {year_range} was given."
    )
    assert year_range_values[0] < year_range_values[1], (
        f"year_range param must have the minimum year first, maximum year second, "
        f"but {year_range} was given."
    )

    kwargs = {
        key: value
        for key, value in event.items()
        if key in VALID_KWARGS and value is not None
    }

    return _response(api.fetch_match_predictions(year_range, **kwargs))


def fetch_match_results(event, _context) -> Response:
    """
    Fetch results data for past matches.

    Params:
    -------
    event: AWS Lambda event dict with the following params:
        start_date: Date string that determines the earliest date
            for which to fetch data. Format is 'yyyy-mm-dd'.
        end_date: Date string that determines the latest date
            for which to fetch data. Format is 'yyyy-mm-dd'.
        fetch_data: Whether to fetch fresh data. Non-fresh data goes up to end
            of previous season.

    Returns:
    --------
    List of match results data in a JSON body.
    """

    kwargs = {}
    if event.get("fetch_data") is not None:
        kwargs["fetch_data"] = event["fetch_data"]

    return _response(
        api.fetch_match_results(event["start_date"], event["end_date"], **kwargs)
    )


def fetch_ml_models() -> Response:
    """
    Fetch general info about all saved ML models.

    Returns:
    --------
    A list of objects with basic info about each ML model in a JSON body.
    """
    return _response(api.fetch_ml_models())
