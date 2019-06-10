from datetime import date
import json
import os
import sys

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__)))

if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

from machine_learning import api


def predictions(request):
    """Responds to any HTTP request.
    Args:
        request (flask.Request): HTTP request object.
    Returns:
        The response text or any set of values that can be turned into a
        Response object using
        `make_response <http://flask.pocoo.org/docs/1.0/api/#flask.Flask.make_response>`.
    """

    auth_token = request.headers.get("Authorization")

    if auth_token != f"Bearer {os.environ.get('GCPF_TOKEN')}":
        return ("Not authorized", 401)

    year = int(request.args.get("year", date.today().year))
    round_number = request.args.get("round_number", None)

    if round_number is not None:
        round_number = int(round_number)

    return json.dumps(api.make_predictions(year, round_number=round_number))
