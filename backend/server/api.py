"""Functions for use by other apps or services to modify Server DB records."""

from typing import List, Tuple, Optional
from datetime import datetime, timedelta
import pytz

from django.utils import timezone
from mypy_extensions import TypedDict
import pandas as pd

from server.models import Match, TeamMatch, Prediction
from server.types import FixtureData, CleanPredictionData, MatchData


MatchDict = TypedDict("MatchDict", {"season": int, "round_number": int})
PredictionValues = TypedDict(
    "PredictionValues",
    {
        "predicted_winner__name": str,
        "predicted_margin": float,
        "predicted_win_probability": float,
    },
)


FIRST_ROUND = 1


def _build_match(match_data: FixtureData) -> Tuple[TeamMatch, TeamMatch]:
    match = Match.get_or_create_from_raw_data(match_data)

    return TeamMatch.get_or_create_from_raw_data(match, match_data)


def update_fixture_data(
    fixture_data: List[FixtureData], upcoming_round: int, verbose=1
) -> None:
    """
    Update or create new Match & TeamMatch records based on raw data.

    Params:
    ------
    fixture_data: Basic data for future matches.
    upcoming_round: The round number for the next match to be played
        (can be the current round if it's ongoing or the next round).
    """
    right_now = timezone.now()

    saved_match_count = Match.objects.filter(
        start_date_time__gt=right_now, round_number=upcoming_round
    ).count()

    if saved_match_count > 0:
        if verbose == 1:
            print(
                f"Already have match records for round {upcoming_round}. "
                "No new data to update."
            )

        return None

    past_matches = [
        fixture_datum
        for fixture_datum in fixture_data
        if fixture_datum["date"] < right_now
    ]
    assert not any(past_matches), (
        "Expected future matches only, but received some past matches as well:\n"
        f"{past_matches}"
    )

    if verbose == 1:
        print(f"Creating new Match and TeamMatch records for round {upcoming_round}...")

    round_number = {match_data["round_number"] for match_data in fixture_data}.pop()
    year = {match_data["year"] for match_data in fixture_data}.pop()

    prev_match = (
        Match.objects.filter(start_date_time__lt=right_now)
        .order_by("-start_date_time")
        .first()
    )

    if prev_match is not None:
        assert round_number in (prev_match.round_number + 1, FIRST_ROUND), (
            "Expected upcoming round number to be 1 greater than previous round "
            f"or 1, but upcoming round is {round_number} in {year}, "
            f" and previous round was {prev_match.round_number} "
            f"in {prev_match.start_date_time.year}"
        )

    for fixture_datum in fixture_data:
        _build_match(fixture_datum)

    if verbose == 1:
        print("Match data saved!\n")

    return None


def backfill_recent_match_results(match_results: List[MatchData], verbose=1) -> None:
    """
    Updates scores for all played matches without score data.

    Params:
    -------
    match_results: List of match dicts that include home & away scores.
    verbose: Whether to print info messages.
    """
    if verbose == 1:
        print("Filling in results for recent matches...")

    earliest_date_time_without_results = Match.earliest_date_time_without_results()

    if earliest_date_time_without_results is None:
        if verbose == 1:
            print("No played matches are missing results.")

        return None

    if not any(match_results):
        print("Results data is not yet available to update match records.")
        return None

    # Subtract a day to have a buffer to allow for mismatched start times,
    # because fixture data have correct start times, but match results data
    # just have basic dates, which means they're given dummy start times,
    # which will be ealier than the actual fixture start time.
    date_time_filter = (  # pylint: disable=unused-variable
        earliest_date_time_without_results - timedelta(days=1)
    )
    right_now = datetime.now(tz=pytz.UTC)  # pylint: disable=unused-variable
    match_results_to_fill = pd.DataFrame(match_results).query(
        "date >= @date_time_filter & date < @right_now"
    )

    if not match_results_to_fill.any().any():
        print("Results data is not yet available to update match records.")
        return None

    Match.update_results(pd.DataFrame(match_results_to_fill))

    return None


def fetch_next_match() -> Optional[MatchDict]:
    """Get the record for the next match to be played."""
    next_match = (
        Match.objects.filter(start_date_time__gt=timezone.now())
        .order_by("start_date_time")
        .first()
    )

    if next_match is None:
        return None

    return {
        "round_number": next_match.round_number,
        "season": next_match.start_date_time.year,
    }


def update_future_match_predictions(predictions: List[CleanPredictionData]) -> None:
    """Update or create prediction records for upcoming matches."""
    future_match_count = Match.objects.filter(
        start_date_time__gt=timezone.now()
    ).count()

    assert future_match_count > 0, (
        "No future matches exist in the DB. Try updating fixture data, "
        "then updating predictions again."
    )

    for pred in predictions:
        Prediction.update_or_create_from_raw_data(pred, future_only=True)


def fetch_latest_round_predictions(verbose=1) -> List[PredictionValues]:
    """
    Return predictions for matches from the current round or next round.

    Params:
    -------
    verbose: Whether to print info messages.
    """
    latest_match = Match.objects.latest("start_date_time")
    latest_year = latest_match.start_date_time.year
    latest_round = latest_match.round_number

    latest_round_predictions = (
        Prediction.objects.filter(
            ml_model__used_in_competitions=True,
            match__start_date_time__year=latest_year,
            match__round_number=latest_round,
        )
        .select_related("match")
        .prefetch_related("match__teammatch_set__team")
        .values(
            "predicted_winner__name",
            "predicted_margin",
            "predicted_win_probability",
        )
    )

    if not any(latest_round_predictions) and verbose == 1:
        print(f"No predictions found for round {latest_round}.")

    return latest_round_predictions
