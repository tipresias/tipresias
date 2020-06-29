"""Module for 'tip' command that updates predictions for upcoming AFL matches."""

from tipping.tipping import Tipper


def main(tipper_class=Tipper, verbose=1) -> None:
    """
    Run 'tip' command for end-to-end tipping process.

    This includes:
    1. Updating data for upcoming matches & backfilling past match data.
    2. Updating or creating predictions for upcoming matches.
    3. Submitting tips to competition websites
        (footytips.com.au & Monash by default).
    """
    tipper = tipper_class(verbose=verbose)
    tipper.fetch_upcoming_fixture()
    tipper.update_match_predictions()
    tipper.submit_tips()


if __name__ == "__main__":
    main()
