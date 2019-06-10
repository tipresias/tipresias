from typing import List, Optional, Dict
import os
import sys
from datetime import date
from functools import partial
import json

import pandas as pd
from sklearn.externals import joblib
from mypy_extensions import TypedDict

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__)))

if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

from machine_learning.ml_data import JoinedMLData
from machine_learning.settings import ML_MODELS


Prediction = TypedDict(
    "Prediction",
    {
        "team": str,
        "year": int,
        "round_number": int,
        "at_home": int,
        "ml_model": str,
        "predicted_margin": float,
    },
)

# We calculate rolling sums/means for some features that can span over 5 seasons
# of data, so we're setting it to 10 to be on the safe side.
N_SEASONS_FOR_PREDICTION = 10
# We want to limit the amount of data loaded as much as possible,
# because we only need the full data set for model training and data analysis,
# and we want to limit memory usage and speed up data processing for tipping
PREDICTION_DATA_START_DATE = f"{date.today().year - N_SEASONS_FOR_PREDICTION}-01-01"


def make_model_predictions(
    year: int,
    data: pd.DataFrame,
    ml_model: Dict[str, str],
    round_number: Optional[int] = None,
) -> List[pd.DataFrame]:
    print(f"Making predictions with {ml_model['name']}")

    loaded_model = joblib.load(os.path.join(BASE_DIR, ml_model["filepath"]))
    data.test_years = (year, year)
    X_test, _ = data.test_data(test_round=round_number)

    if not X_test.any().any():
        raise ValueError(
            "X_test doesn't have any rows, likely due to some data for the "
            "upcoming round not being available yet."
        )

    y_pred = loaded_model.predict(X_test)

    data_row_slice = (slice(None), year, slice(round_number, round_number))

    return (
        data.data.loc[data_row_slice, :]
        .assign(predicted_margin=y_pred, ml_model=ml_model["name"])
        .set_index("ml_model", append=True, drop=False)
    )


def make_predictions(
    year: int,
    round_number: Optional[int] = None,
    ml_models: List[Dict[str, str]] = ML_MODELS,
    data: pd.DataFrame = JoinedMLData(
        fetch_data=True, start_date=PREDICTION_DATA_START_DATE
    ),
) -> List[Prediction]:
    if not any(ml_models):
        raise ValueError("Could not find any ML models in to make predictions.\n")

    partial_make_model_predictions = partial(
        make_model_predictions, year, data, round_number=round_number
    )

    return (
        pd.concat([partial_make_model_predictions(ml_model) for ml_model in ml_models])
        .loc[
            :,
            ["team", "year", "round_number", "ml_model", "at_home", "predicted_margin"],
        ]
        .to_dict("records")
    )


def predictions(request):
    """Responds to any HTTP request.
    Args:
        request (flask.Request): HTTP request object.
    Returns:
        The response text or any set of values that can be turned into a
        Response object using
        `make_response <http://flask.pocoo.org/docs/1.0/api/#flask.Flask.make_response>`.
    """

    year = request.args.get("year", date.today().year)
    round_number = request.args.get("round_number", None)

    return json.dumps(make_predictions(year, round_number=round_number))
