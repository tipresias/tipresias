import os
import sys
from datetime import date
import json

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__)))

if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

from machine_learning import api


TRUE = "true"
FALSE = "false"


def _unauthorized_response():
    return ("Not authorized", 401)


def _request_is_authorized(request) -> bool:
    auth_token = request.headers.get("Authorization")

    if auth_token == f"Bearer {os.getenv('GCPF_TOKEN')}":
        return True

    return False


def predictions(request):
    """
    Generates predictions for the given year and round number, and returns the data
    as an HTTP response.

    Params:
        year_range (str, optional): Year range for which you want prediction data.
            Format = yyyy-yyyy.
            Default = current year only.
        round_number (int, optional): Round number for which you want prediction data.
            Default = All rounds for given year.
        ml_models (str, optional): Comma-separated list of names of ML model to use
            for making predictions.
            Default = All available models
    Args:
        request (flask.Request): HTTP request object.
    Returns:
        flask.Response with a body that has a JSON of prediction data.
    """

    if not _request_is_authorized(request):
        return _unauthorized_response()

    this_year = date.today().year
    year_range_param = request.args.get("year_range", f"{this_year}-{this_year + 1}")
    year_range = tuple([int(year) for year in year_range_param.split("-")])

    round_number = request.args.get("round_number", None)
    round_number = int(round_number) if round_number is not None else None

    ml_models_param = request.args.get("ml_models", None)
    ml_models_param = (
        ml_models_param.split(",") if ml_models_param is not None else None
    )

    return json.dumps(
        api.make_predictions(
            year_range, round_number=round_number, ml_model_names=ml_models_param
        )
    )


def fixtures(request):
    """
    Fetches fixture data for the given date range, and returns the data
    as an HTTP response.

    Params:
        start_date (string of form 'yyyy-mm-dd', required): Start of date range
            (inclusive) for which you want data.
        start_date (string of form 'yyyy-mm-dd', required): End of date range
            (inclusive) for which you want data.
    Args:
        request (flask.Request): HTTP request object.
    Returns:
        flask.Response with a body that has a JSON of fixture data.
    """

    if not _request_is_authorized(request):
        return _unauthorized_response()

    start_date = request.args.get("start_date")
    end_date = request.args.get("end_date")

    return json.dumps(api.fetch_fixture_data(start_date, end_date))


def match_results(request):
    """
    Fetches match results data for the given date range, and returns the data
    as an HTTP response.

    Params:
        start_date (string of form 'yyyy-mm-dd', required): Start of date range
            (inclusive) for which you want data.
        start_date (string of form 'yyyy-mm-dd', required): End of date range
            (inclusive) for which you want data.
        fetch_data (string, 'true' or 'false'): Whether to fetch fresh data,
            will take longer if true. Default = 'false'
    Args:
        request (flask.Request): HTTP request object.
    Returns:
        flask.Response with a body that has a JSON of match results data.
    """

    if not _request_is_authorized(request):
        return _unauthorized_response()

    start_date = request.args.get("start_date")
    end_date = request.args.get("end_date")
    fetch_data = request.args.get("fetch_data", FALSE).lower() == TRUE

    return json.dumps(
        api.fetch_match_results_data(start_date, end_date, fetch_data=fetch_data)
    )


def ml_models(request):
    """
    Fetches info for all available ML models and returns the data as an HTTP response.

    Args:
        request (flask.Request): HTTP request object.
    Returns:
        flask.Response with a body that has a JSON of ML model data.
    """

    if not _request_is_authorized(request):
        return _unauthorized_response()

    return json.dumps(api.fetch_ml_model_info())
