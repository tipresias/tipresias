"""One-off script for backfilling winner & margin fields for past matches."""

import os
import sys

import django

PROJECT_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "../"))

if PROJECT_PATH not in sys.path:
    sys.path.append(PROJECT_PATH)

django.setup()

from server.models import Match  # pylint: disable=wrong-import-position


def main():
    """Backfill winner & margin for existing matches."""
    for match in Match.objects.all():
        match._save_result()  # pylint: disable=protected-access


if __name__ == "__main__":
    main()
