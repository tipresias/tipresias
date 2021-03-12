"""Settings for the server app in the test environment."""

from project.settings.common import *  # pylint: disable=wildcard-import, unused-wildcard-import

ALLOWED_HOSTS = ["backend", "localhost", "app"]
CORS_ALLOWED_ORIGINS = [
    "http://frontend:3000",
    "http://localhost:3000",
    "http://host.docker.internal:3000",
]

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = "^6&#7de5dx#eqg6dm^l3#@wj6vjjn%2f=u(!&ia()h-l1ppan!"

ENVIRONMENT = "test"
