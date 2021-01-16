"""Session setup/teardown for integration tests."""

import os
import re
from contextlib import contextmanager

import pytest
from sqlalchemy import create_engine
from sqlalchemy.dialects import registry


CAPTURED_MATCH = 1

registry.register("fauna", "tipping.db.sqlalchemy_fauna.dialect", "FaunaDialect")


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

    try:
        yield secret_key
    finally:
        os.system("npx fauna delete-database test --endpoint localhost")


@pytest.fixture(scope="function")
def fauna_secret():
    """Set up and tear down test DB in local Fauna instance.

    Passes the generated key to the test function.
    """
    with _setup_teardown_test_db() as secret_key:
        yield secret_key


@pytest.fixture(scope="function")
def fauna_engine():
    """Set up and tear down test DB in local Fauna instance.

    Passes the SQLAlchemy engine for the test DB to the test function.
    """
    with _setup_teardown_test_db() as secret_key:
        engine = create_engine(f"fauna://faunadb:8443/?secret={secret_key}")

        yield engine
