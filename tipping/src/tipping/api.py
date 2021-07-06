"""External-facing API for fetching and updating application data."""

from typing import Optional
from datetime import datetime, timezone
from warnings import warn

import pandas as pd

from tipping import data_import, data_export
from tipping.helpers import pivot_team_matches_to_matches
from tipping.tipping import MonashSubmitter

# from tipping.models import Match
# from tipping import settings


DEC = 12
THIRTY_FIRST = 31
JAN = 1
FIRST = 1


def _select_matches_from_current_round(
    fixture_data_frame: pd.DataFrame, beginning_of_today: datetime, after=True
) -> Optional[pd.DataFrame]:
    if not fixture_data_frame.any().any():
        warn(
            "Fixture for the upcoming round haven't been posted yet, "
            "so there's nothing to tip. Try again later."
        )

        return None

    latest_match_date = fixture_data_frame["date"].max()

    if beginning_of_today > latest_match_date and after:
        warn(
            f"No matches found after {beginning_of_today}. The latest match "
            f"found is at {latest_match_date}\n"
        )

        return None

    date_comparison = ">" if after else "<"
    latest_round_numbers = fixture_data_frame.query(
        f"date {date_comparison} @beginning_of_today"
    ).loc[:, "round_number"]

    if not any(latest_round_numbers):
        return None

    current_round = int(  # pylint: disable=unused-variable
        latest_round_numbers.min() if after else latest_round_numbers.max()
    )

    fixture_for_current_round = fixture_data_frame.query(
        "round_number == @current_round"
    )

    return fixture_for_current_round


def _fetch_current_round_fixture(verbose, after=True) -> Optional[pd.DataFrame]:
    right_now = datetime.now(tz=timezone.utc)
    beginning_of_today = right_now.replace(hour=0, minute=0, second=0, microsecond=0)
    beginning_of_this_year = datetime(
        beginning_of_today.year, JAN, FIRST, tzinfo=timezone.utc
    )
    end_of_this_year = datetime(
        beginning_of_today.year, DEC, THIRTY_FIRST, tzinfo=timezone.utc
    )

    if verbose == 1:
        preposition = "after" if after else "up to"
        print(f"Fetching fixture for matches {preposition} {beginning_of_today}...\n")

    fixture_data_frame = data_import.DataImporter().fetch_fixture_data(
        start_date=beginning_of_this_year,
        end_date=end_of_this_year,
    )

    return _select_matches_from_current_round(
        fixture_data_frame, beginning_of_today, after=after
    )


def update_fixture_data(verbose: int = 1) -> None:
    """
    Fetch fixture data and send upcoming match data to the main app.

    Params:
    -------
    verbose: How much information to print. 1 prints all messages; 0 prints none.
    """
    right_now = datetime.now(tz=timezone.utc)  # pylint: disable=unused-variable

    matches_from_upcoming_round = _fetch_current_round_fixture(verbose)

    if matches_from_upcoming_round is None:
        return None

    upcoming_round = (
        matches_from_upcoming_round["round_number"].drop_duplicates().iloc[0]
    )
    future_matches = matches_from_upcoming_round.query("date > @right_now")

    data_export.update_fixture_data(future_matches, upcoming_round)

    # Disabled until I can fix the bugs with the FQL queries when the foreign key value
    # is blank.
    # db_session = settings.Session()
    # matches = Match.from_future_fixtures(db_session, future_matches, upcoming_round)

    # for match in matches:
    #     db_session.add(match)

    # db_session.commit()

    return None


def update_match_predictions(
    tips_submitters=None, verbose=1, ml_model_names: Optional[str] = None
) -> None:
    """Fetch predictions from ML models and send them to the main app.

    Params:
    -------
    tips_submitters: Objects that handle submission of tips to competitions sites.
    verbose: How much information to print. 1 prints all messages; 0 prints none.
    ml_model_names: Comma-separated string of ML model names to use
        for making predictions.
    """
    matches_from_current_round = _fetch_current_round_fixture(verbose)

    if matches_from_current_round is None:
        return None

    current_round = matches_from_current_round["round_number"].min()
    current_season = matches_from_current_round["date"].min().year

    if verbose == 1:
        print("Fetching predictions for round " f"{current_round}, {current_season}...")

    prediction_data = data_import.DataImporter().fetch_prediction_data(
        f"{current_season}-{current_season + 1}",
        round_number=current_round,
        ml_model_names=ml_model_names,
    )

    if verbose == 1:
        print("Predictions received!")

    match_predictions = pivot_team_matches_to_matches(prediction_data)
    updated_prediction_records = data_export.update_match_predictions(match_predictions)

    if verbose == 1:
        print("Match predictions sent!")

    if not updated_prediction_records.any().any():
        if verbose == 1:
            print(
                "No predictions found for the upcoming round. "
                "Not submitting any tips."
            )

        return None

    tips_submitters = tips_submitters or [
        MonashSubmitter(verbose=verbose),
    ]

    for submitter in tips_submitters:
        submitter.submit_tips(updated_prediction_records)

    return None


def update_matches(verbose=1) -> None:
    """
    Fetch match data and send them to the main app.

    verbose: How much information to print. 1 prints all messages; 0 prints none.
    """
    right_now = datetime.now()
    start_of_year = datetime(right_now.year, JAN, FIRST).strftime("%Y-%m-%d")
    end_of_year = datetime(right_now.year, DEC, THIRTY_FIRST).strftime("%Y-%m-%d")

    if verbose == 1:
        print(f"Fetching match data for season {right_now.year}")

    match_data = data_import.DataImporter().fetch_match_data(
        start_of_year, end_of_year, fetch_data=True
    )

    if verbose == 1:
        print("Match data received!")

    data_export.update_matches(match_data)

    if verbose == 1:
        print("Match data sent!")


def update_match_results(verbose=1) -> None:
    """
    Fetch minimal match results data and send them to the main app.

    verbose: How much information to print. 1 prints all messages; 0 prints none.
    """
    matches_from_current_round = _fetch_current_round_fixture(verbose, after=False)

    if matches_from_current_round is None:
        return None

    current_round = matches_from_current_round["round_number"].min()

    if verbose == 1:
        print(f"Fetching match results for round {current_round}")

    match_results_data = data_import.DataImporter().fetch_match_results_data(
        current_round
    )

    if verbose == 1:
        print("Match results data received!")

    data_export.update_match_results(match_results_data)

    if verbose == 1:
        print("Match data sent!")

    return None


def fetch_match_predictions(
    year_range: str,
    round_number: Optional[int] = None,
    ml_models: Optional[str] = None,
    train_models: Optional[bool] = False,
) -> pd.DataFrame:
    """
    Fetch prediction data from ML models.

    Params:
    -------
    year_range: Min (inclusive) and max (exclusive) years for which to fetch data.
        Format is 'yyyy-yyyy'.
    round_number: Specify a particular round for which to fetch data.
    ml_models: Comma-separated string of ML model names to use
        for making predictions.
    train_models: Whether to train models in between predictions (only applies
        when predicting across multiple seasons).

    Returns:
    --------
        List of prediction data dictionaries.
    """
    prediction_data = data_import.DataImporter().fetch_prediction_data(
        year_range,
        round_number=round_number,
        ml_model_names=ml_models,
        train_models=train_models,
    )

    return pivot_team_matches_to_matches(prediction_data)


def fetch_matches(
    start_date: str, end_date: str, fetch_data: bool = False
) -> pd.DataFrame:
    """
    Fetch results data for past matches.

    Params:
    -------
    start_date: Date-time string that determines the earliest date
        for which to fetch data. Format is 'yyyy-mm-dd'.
    end_date: Date-time string that determines the latest date
        for which to fetch data. Format is 'yyyy-mm-dd'.
    fetch_data: Whether to fetch fresh data. Non-fresh data goes up to end
        of previous season.

    Returns:
    --------
        List of match results data dicts.
    """
    return data_import.DataImporter().fetch_match_data(
        start_date, end_date, fetch_data=fetch_data
    )


def fetch_ml_models() -> pd.DataFrame:
    """
    Fetch general info about all saved ML models.

    Returns:
    --------
    A list of objects with basic info about each ML model.
    """
    return data_import.DataImporter().fetch_ml_model_info()
