"""Functions for use by other apps or services to modify Server DB records."""

from typing import List, Tuple, Optional

from django.utils import timezone
from mypy_extensions import TypedDict

from server.models import Match, TeamMatch
from server.types import FixtureData
from data import data_import


MatchDict = TypedDict("MatchDict", {"season": int, "round_number": int},)

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
                f"{saved_match_count} unplayed match records found for round {upcoming_round}. "
                "Updating associated prediction records with new model predictions.\n"
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

    prev_match = Match.objects.order_by("-start_date_time").first()

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


def backfill_recent_match_results(verbose=1) -> None:
    """Updates scores for all played matches without score data."""
    if verbose == 1:
        print("Filling in results for recent matches...")

    earliest_date_without_results = Match.earliest_date_without_results()

    if earliest_date_without_results is None:
        if verbose == 1:
            print("No played matches are missing results.")

        return None

    match_results = data_import.fetch_match_results_data(
        earliest_date_without_results, timezone.now(), fetch_data=True
    )

    if not any(match_results):
        print("Results data is not yet available to update match records.")
        return None

    Match.update_results(match_results)

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
