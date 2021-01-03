"""Session setup/teardown for integration tests."""

import os
from unittest.mock import patch
import re
from contextlib import contextmanager

import pytest

from tipping.db.faunadb import FaunadbClient


CAPTURED_MATCH = 1


@pytest.fixture(scope="session", autouse=True)
def _setup_faunadb():
    os.system(
        "npx fauna add-endpoint http://faunadb:8443/ --alias localhost --key secret"
    )


@contextmanager
def _setup_teardown_test_db():
    os.system("npx fauna create-database test --endpoint localhost")

    create_key_output = os.popen(
        "npx fauna create-key test --endpoint=localhost"
    ).read()
    secret_key = (
        re.search("secret: (.+)", create_key_output).group(CAPTURED_MATCH).strip()
    )

    with patch("tipping.db.faunadb.settings.FAUNADB_KEY", secret_key):
        try:
            yield secret_key
        finally:
            os.system("npx fauna delete-database test --endpoint localhost")


@pytest.fixture(scope="function")
def faunadb_client():
    """Set up and tear down test DB in local FaunaDB instance.

    Passes the created Faunadb client to the test function.
    """
    with _setup_teardown_test_db() as secret_key:
        client = FaunadbClient(faunadb_key=secret_key)
        client.import_schema()

        yield client


@pytest.fixture(scope="function")
def fauna_secret():
    """Set up and tear down test DB in local Fauna instance.

    Passes the generated key to the test function.
    """
    with _setup_teardown_test_db() as secret_key:
        yield secret_key
