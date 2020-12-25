"""External-facing API for fetching and updating application data."""

from typing import Optional, List
from datetime import datetime, timezone
from warnings import warn

import pandas as pd

from tipping import data_import, data_export
from tipping.helpers import pivot_team_matches_to_matches
from tipping.tipping import MonashSubmitter, FootyTipsSubmitter
from tipping.models import Match, TeamMatch, Prediction

DEC = 12
THIRTY_FIRST = 31
JAN = 1
FIRST = 1
FIRST_ROUND = 1


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

    fixture_data_frame = data_import.fetch_fixture_data(
        start_date=beginning_of_this_year,
        end_date=end_of_this_year,
    )

    matches_from_current_round = _select_matches_from_current_round(
        fixture_data_frame, beginning_of_today, after=after
    )

    return matches_from_current_round


def _update_faunadb_fixture_data(
    fixture_data: pd.DataFrame, current_round: int, verbose: int = 1
):
    right_now = datetime.now(tz=timezone.utc)
    season_matches = Match.filter_by_season(season=right_now.year)

    saved_match_count = season_matches.filter(round=current_round).count()

    if saved_match_count > 0:
        if verbose == 1:
            print(
                f"Already have match records for round {current_round}. "
                "No new data to update."
            )

        return None

    past_fixture_matches = [
        fixture_datum
        for _, fixture_datum in fixture_data.iterrows()
        if fixture_datum["date"] < right_now
    ]
    assert len(past_fixture_matches) == 0, (
        "Expected future matches only, but received some past matches as well:\n"
        f"{past_fixture_matches}"
    )

    if verbose == 1:
        print(f"Creating new Match and TeamMatch records for round {current_round}...")

    round_number = {
        match_data["round_number"] for _, match_data in fixture_data.iterrows()
    }.pop()
    year = {match_data["year"] for _, match_data in fixture_data.iterrows()}.pop()

    past_matches = season_matches.filter(start_date_time__lt=right_now)
    prev_match = (
        max(past_matches, key=lambda match: match.start_date_time)
        if any(past_matches)
        else None
    )

    if prev_match is not None:
        assert round_number in (prev_match.round_number + 1, FIRST_ROUND), (
            "Expected upcoming round number to be 1 greater than previous round "
            f"or 1, but upcoming round is {round_number} in {year}, "
            f" and previous round was {prev_match.round_number} "
            f"in {prev_match.start_date_time.year}"
        )

    for _, fixture_datum in fixture_data.iterrows():
        match = Match.get_or_create_from_raw_data(fixture_datum)
        team_matches = TeamMatch.from_raw_data(fixture_datum, match=match)

        for team_match in team_matches:
            team_match.create()

    if verbose == 1:
        print("Match data saved!\n")

    return None


def update_fixture_data(verbose: int = 1) -> None:
    """
    Fetch fixture data and send upcoming match data to the main app.

    Params:
    -------
    verbose: How much information to print. 1 prints all messages; 0 prints none.
    """
    right_now = datetime.now(tz=timezone.utc)  # pylint: disable=unused-variable

    matches_from_current_round = _fetch_current_round_fixture(verbose)

    if matches_from_current_round is None:
        return None

    current_round = matches_from_current_round["round_number"].drop_duplicates().iloc[0]
    future_matches = matches_from_current_round.query("date > @right_now")

    data_export.update_fixture_data(future_matches, current_round)
    _update_faunadb_fixture_data(future_matches, current_round, verbose=verbose)

    return None


def _update_faunadb_predictions(predictions: pd.DataFrame):
    for _, pred in predictions.iterrows():
        Prediction.update_or_create_from_raw_data(pred)


def update_match_predictions(tips_submitters=None, verbose=1) -> None:
    """Fetch predictions from ML models and send them to the main app.

    Params:
    -------
    tips_submitters: Objects that handle submission of tips to competitions sites.
    verbose: How much information to print. 1 prints all messages; 0 prints none.
    """
    matches_from_current_round = _fetch_current_round_fixture(verbose)

    if matches_from_current_round is None:
        return None

    current_round = matches_from_current_round["round_number"].min()
    current_season = matches_from_current_round["date"].min().year

    if verbose == 1:
        print("Fetching predictions for round " f"{current_round}, {current_season}...")

    prediction_data = data_import.fetch_prediction_data(
        f"{current_season}-{current_season + 1}",
        round_number=current_round,
    )

    if verbose == 1:
        print("Predictions received!")

    match_predictions = pivot_team_matches_to_matches(prediction_data)
    updated_prediction_records = data_export.update_match_predictions(match_predictions)

    _update_faunadb_predictions(match_predictions)

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
        FootyTipsSubmitter(verbose=verbose),
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
    start_of_year = datetime(right_now.year, JAN, FIRST)
    end_of_year = datetime(right_now.year, DEC, THIRTY_FIRST)

    if verbose == 1:
        print(f"Fetching match data for season {right_now.year}")

    match_data = data_import.fetch_match_data(
        str(start_of_year), str(end_of_year), fetch_data=True
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

    match_results_data = data_import.fetch_match_results_data(current_round)

    if verbose == 1:
        print("Match results data received!")

    data_export.update_match_results(match_results_data)

    if verbose == 1:
        print("Match data sent!")

    return None


def fetch_match_predictions(
    year_range: str,
    round_number: Optional[int] = None,
    ml_models: Optional[List[str]] = None,
    train_models: Optional[bool] = False,
) -> pd.DataFrame:
    """
    Fetch prediction data from ML models.

    Params:
    -------
    year_range: Min (inclusive) and max (exclusive) years for which to fetch data.
        Format is 'yyyy-yyyy'.
    round_number: Specify a particular round for which to fetch data.
    ml_models: List of ML model names to use for making predictions.
    train_models: Whether to train models in between predictions (only applies
        when predicting across multiple seasons).

    Returns:
    --------
        List of prediction data dictionaries.
    """
    prediction_data = data_import.fetch_prediction_data(
        year_range,
        round_number=round_number,
        ml_models=ml_models,
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
    return data_import.fetch_match_data(start_date, end_date, fetch_data=fetch_data)


def fetch_ml_models() -> pd.DataFrame:
    """
    Fetch general info about all saved ML models.

    Returns:
    --------
    A list of objects with basic info about each ML model.
    """
    return data_import.fetch_ml_model_info()
