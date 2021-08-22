"""Session setup/teardown for integration tests."""

import os
import re
from contextlib import contextmanager
from unittest.mock import patch
import subprocess

import pytest
from sqlalchemy import create_engine
from sqlalchemy.dialects import registry

from tests.fixtures import Session


CAPTURED_MATCH = 1

registry.register("fauna", "sqlalchemy_fauna.dialect", "FaunaDialect")


@pytest.fixture(scope="session", autouse=True)
def _setup_faunadb():
    subprocess.run(
        "npx fauna add-endpoint http://faunadb:8443/ --alias localhost --key secret",
        check=True,
        shell=True,
    )


@contextmanager
def _setup_teardown_test_db():
    subprocess.run(
        "npx fauna create-database test --endpoint localhost",
        check=True,
        shell=True,
    )

    try:
        create_key_output = subprocess.run(
            "npx fauna create-key test --endpoint=localhost",
            check=True,
            shell=True,
            capture_output=True,
            encoding="utf8",
        )
        secret_key = (
            re.search("secret: (.+)", create_key_output.stdout)
            .group(CAPTURED_MATCH)
            .strip()
        )

        with patch.dict(os.environ, {**os.environ, "FAUNA_SECRET": secret_key}):
            subprocess.run("alembic upgrade head", check=True, shell=True)

            yield secret_key
    finally:
        subprocess.run(
            "npx fauna delete-database test --endpoint localhost",
            check=True,
            shell=True,
        )


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


@pytest.fixture(scope="function")
def fauna_session():
    """Set up an SQLAlchemy DB session for use in tests."""
    with _setup_teardown_test_db() as secret_key:
        engine = create_engine(f"fauna://faunadb:8443/?secret={secret_key}")
        Session.configure(bind=engine)

        with patch("tipping.settings.Session", Session):
            session = Session()

            yield session

        Session.remove()
