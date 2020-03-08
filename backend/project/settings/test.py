"""Settings for the server app in the test environment."""

from project.settings.common import *  # pylint: disable=wildcard-import, unused-wildcard-import

ALLOWED_HOSTS = ["backend", "localhost", "app"]

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = "^6&#7de5dx#eqg6dm^l3#@wj6vjjn%2f=u(!&ia()h-l1ppan!"

ENVIRONMENT = "test"
