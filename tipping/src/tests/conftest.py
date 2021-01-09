"""Session setup/teardown for all tests."""

import os

# This seems to be the only way to globally remove the FAUNA_SECRET,
# so we don't accidentally make calls to the development DB.
os.environ["FAUNA_SECRET"] = ""
