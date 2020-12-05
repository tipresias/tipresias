"""Session setup/teardown for all tests."""

import os

# This seems to be the only way to globally remove the FAUNADB_KEY,
# so we don't accidentally make calls to the development DB.
os.environ["FAUNADB_KEY"] = ""
