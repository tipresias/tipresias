"""Functions for use by other apps or services to modify Server DB records."""

from typing import List, Tuple

from django.utils import timezone

from server.models import Match, TeamMatch
from server.types import FixtureData


FIRST_ROUND = 1


def _build_match(match_data: FixtureData) -> Tuple[TeamMatch, TeamMatch]:
    match = Match.get_or_create_from_raw_data(match_data)

    return TeamMatch.get_or_create_from_raw_data(match, match_data)


def update_match_data(
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
