"""Module for 'tip' command that updates predictions for upcoming AFL matches."""

from django.core.management.base import BaseCommand

from data.tipping import Tipper


class Command(BaseCommand):
    """manage.py command for 'tip' that updates predictions for upcoming AFL matches."""

    help = """
    Check if there are upcoming AFL matches and make predictions on results
    for all unplayed matches in the upcoming/current round.
    """

    def handle(self, *_args, verbose=1, **_kwargs) -> None:  # pylint: disable=W0221
        """
        Run 'tip' command for end-to-end tipping process.

        This includes:
        1. Updating data for upcoming matches & backfilling past match data.
        2. Updating or creating predictions for upcoming matches.
        3. Submitting tips to competition websites
            (footytips.com.au & Monash by default).
        """
        tipper = Tipper(verbose=verbose)
        tipper.fetch_upcoming_fixture()
        tipper.update_match_predictions()
        tipper.submit_tips()
