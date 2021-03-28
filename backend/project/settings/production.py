"""Settings for the server app in the production environment."""

import dj_database_url

# pylint: disable=W0401,W0614
from project.settings.common import *

ENVIRONMENT = "production"

SECRET_KEY = os.environ["SECRET_KEY"]
API_TOKEN = os.environ["API_TOKEN"]
TIPPING_SERVICE_TOKEN = os.environ["TIPPING_SERVICE_TOKEN"]
ROLLBAR_TOKEN = os.getenv("ROLLBAR_TOKEN", "")

TIPPING_SERVICE = "TBD"

ALLOWED_HOSTS = [
    "tipresias.herokuapp.com",
    ".tipresias.net",
    os.environ.get("PRODUCTION_HOST", ""),
    os.environ.get("DATA_SCIENCE_SERVICE", ""),
]

CORS_ALLOWED_ORIGIN_REGEXES = [
    r"^https?:\/\/(?:w{3}\.)?tipresias.net$",
    os.getenv("FRONTEND_SERVICE", ""),
]

MIDDLEWARE.append("rollbar.contrib.django.middleware.RollbarNotifierMiddleware")

if os.environ.get("DATABASE_URL"):
    DATABASES["default"] = dj_database_url.config(conn_max_age=600, ssl_require=True)

ROLLBAR = {
    "access_token": ROLLBAR_TOKEN,
    "environment": ENVIRONMENT,
    "branch": "master",
    "root": BASE_DIR,
}
