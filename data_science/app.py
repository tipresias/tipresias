import os
import sys
from datetime import date

from bottle import Bottle, run, request

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__)))
SRC_PATH = os.path.join(BASE_DIR, "src")

if SRC_PATH not in sys.path:
    sys.path.append(SRC_PATH)

os.environ["PYTHONPATH"] = SRC_PATH + os.pathsep + os.environ.get("PYTHONPATH", "")

from machine_learning import api


TRUE = "true"
FALSE = "false"

app = Bottle()


@app.route("/predictions")
def predictions():
    """
    Generates predictions for the given year and round number, and returns the data
    as an HTTP response.

    Params:
        year_range (str, optional): Year range for which you want prediction data.
            Format = yyyy-yyyy.
            Default = current year only.
        round_number (int, optional): Round number for which you want prediction data.
            Default = All rounds for given year.
        ml_models (str, optional): Name of the ML model to use for making predictions.
            Default = All available models
    Returns:
        flask.Response with a body that has a JSON of prediction data.
    """

    this_year = date.today().year
    year_range_param = request.query.year_range or f"{this_year}-{this_year + 1}"
    year_range = tuple([int(year) for year in year_range_param.split("-")])

    round_number = request.query.round_number
    round_number = int(round_number) if round_number is not None else None

    ml_models_param = request.query.ml_models
    ml_models_param = (
        ml_models_param.split(",") if ml_models_param is not None else None
    )

    return api.make_predictions(
        year_range, round_number=round_number, ml_model_names=ml_models_param
    )


@app.route("/fixtures")
def fixtures():
    """
    Fetches fixture data for the given date range, and returns the data
    as an HTTP response.

    Params:
        start_date (string of form 'yyyy-mm-dd', required): Start of date range
            (inclusive) for which you want data.
        start_date (string of form 'yyyy-mm-dd', required): End of date range
            (inclusive) for which you want data.
    Returns:
        flask.Response with a body that has a JSON of fixture data.
    """

    start_date = request.query.start_date
    end_date = request.query.end_date

    return api.fetch_fixture_data(start_date, end_date)


@app.route("/match_results")
def match_results():
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
    Returns:
        flask.Response with a body that has a JSON of match results data.
    """

    start_date = request.query.start_date
    end_date = request.query.end_date
    fetch_data = (request.query.fetch_data or FALSE).lower() == TRUE

    return api.fetch_match_results_data(start_date, end_date, fetch_data=fetch_data)


@app.route("/ml_models")
def ml_models():
    """
    Fetches info for all available ML models and returns the data as an HTTP response.

    Returns:
        flask.Response with a body that has a JSON of ML model data.
    """

    return api.fetch_ml_model_info()


run(app, host="0.0.0.0", port=8008, reloader=True)
