"""
Module for 'backfill_results' command that updates scores for recently-played matches.
"""

from django.core.management.base import BaseCommand

from server.api import backfill_recent_match_results


class Command(BaseCommand):
    """manage.py command for 'backfill_results' that updates scores for past matches."""

    help = """
    Check if there are past AFL matches without scores and update them
    with actual final scores.
    """

    def handle(self, *_args, verbose=1, **_kwargs) -> None:  # pylint: disable=W0221
        """Run 'backfill_results' command to update past matches with scores."""
        backfill_recent_match_results(verbose=verbose)
