"""Session setup/teardown for integration tests."""

import os
from unittest.mock import patch
import re

import pytest

from tipping.db.faunadb import FaunadbClient


CAPTURED_MATCH = 1


@pytest.fixture(scope="session", autouse=True)
def _setup_faunadb():
    os.system(
        "npx fauna add-endpoint http://faunadb:8443/ --alias localhost --key secret"
    )


@pytest.fixture(scope="function")
def faunadb_client():
    """Set up and tear down test DB in local FaunaDB instance."""
    os.system("npx fauna create-database test --endpoint localhost")

    create_key_output = os.popen(
        "npx fauna create-key test --endpoint=localhost"
    ).read()

    faunadb_key = (
        re.search("secret: (.+)", create_key_output).group(CAPTURED_MATCH).strip()
    )

    client = FaunadbClient(faunadb_key=faunadb_key)
    client.import_schema()

    with patch("tipping.db.faunadb.settings.FAUNADB_KEY", faunadb_key):
        yield client

    os.system("npx fauna delete-database test --endpoint localhost")
