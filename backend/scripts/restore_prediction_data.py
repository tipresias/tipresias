"""
One-off script for restoring 2019 predictions data from a saved data file after
resetting the production database
"""

# pylint: disable=import-error

import os
import sys

import pandas as pd
import django
from django.db import transaction

PROJECT_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "../"))

if PROJECT_PATH not in sys.path:
    sys.path.append(PROJECT_PATH)

django.setup()

from project.settings.common import DATA_DIR

# NOTE: These imports are no longer valid with the refactoring of machine_learning
# into a separate service, so this code will have to be updated if we want to use it
# again.
from machine_learning.data_import import FitzroyDataImporter
from machine_learning.data_transformation.data_cleaning import clean_match_data
from server.models import Match, TeamMatch, Prediction, Team, MLModel

FILENAME = "2019-prediction-data-2019-05-26.csv"
SEASON_TO_RESTORE = 2019


def build_prediction(prediction):
    match_record = Match.objects.get(
        round_number=prediction["match__round_number"],
        start_date_time__year=prediction["match__start_date_time__year"],
        teammatch__team__name=prediction["match__teammatch__team__name"],
    )
    ml_model_record = MLModel.objects.get(name=prediction["ml_model__name"])
    predicted_winner_record = Team.objects.get(
        name=prediction["predicted_winner__name"]
    )

    prediction_record, was_created = Prediction.objects.get_or_create(
        match=match_record,
        predicted_winner=predicted_winner_record,
        predicted_margin=prediction["predicted_margin"],
        ml_model=ml_model_record,
    )

    if was_created:
        prediction_record.full_clean()


def build_team_matches(match_record, match_data):
    home_team = Team.objects.get(name=match_data["home_team"])
    away_team = Team.objects.get(name=match_data["away_team"])

    home_record, home_was_created = TeamMatch.objects.get_or_create(
        match=match_record, team=home_team, at_home=True, score=match_data["home_score"]
    )

    if home_was_created:
        home_record.full_clean()

    away_record, away_was_created = TeamMatch.objects.get_or_create(
        match=match_record,
        team=away_team,
        at_home=False,
        score=match_data["away_score"],
    )

    if away_was_created:
        away_record.full_clean()


def build_match(match_data):
    match_record, was_created = Match.objects.get_or_create(
        start_date_time=match_data["date"],
        round_number=match_data["round_number"],
        venue=match_data["venue"],
    )

    if was_created:
        match_record.full_clean()
        build_team_matches(match_record, match_data)


def main(data_reader=FitzroyDataImporter(), year=SEASON_TO_RESTORE):
    match_data = data_reader.match_results(
        start_date=f"{year}-01-01", end_date=f"{year}-12-31", fetch_data=True
    ).pipe(clean_match_data)
    # Due to the nature of the query to collect the prediction records, home and
    # away teams get their own rows, but we just need one row per match,
    # dropping team_match duplicates
    prediction_data = pd.read_csv(os.path.join(DATA_DIR, FILENAME)).drop_duplicates(
        subset=[
            "match__round_number",
            "match__start_date_time__year",
            "ml_model__name",
            "predicted_winner__name",
        ]
    )

    with transaction.atomic():
        for match in match_data.to_dict("records"):
            build_match(match)

    with transaction.atomic():
        for prediction in prediction_data.to_dict("records"):
            build_prediction(prediction)


if __name__ == "__main__":
    main()
