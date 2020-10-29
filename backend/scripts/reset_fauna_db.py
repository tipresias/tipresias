# pylint: disable=wrong-import-position
"""One-off script to load existing data from Postgres DB dump to FaunaDB."""

import os
import sys

import django

PROJECT_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "../"))

if PROJECT_PATH not in sys.path:
    sys.path.append(PROJECT_PATH)

django.setup()

from server.db.faunadb import FaunadbClient


def main():
    """Load existing data from Postgres DB dump to FaunaDB."""
    FaunadbClient.import_schema(mode="override")


if __name__ == "__main__":
    main()
