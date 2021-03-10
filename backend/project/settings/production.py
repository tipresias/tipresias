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
    os.environ.get("PRODUCTION_HOST"),
    os.environ.get("DATA_SCIENCE_SERVICE"),
]

if os.getenv("FRONTEND_SERVICE"):
    CORS_ORIGIN_WHITELIST = (os.getenv("FRONTEND_SERVICE", ""),)

INSTALLED_APPS.append("whitenoise.runserver_nostatic")

# Must insert after SecurityMiddleware, which is first in settings/common.py
MIDDLEWARE.insert(1, "whitenoise.middleware.WhiteNoiseMiddleware")
MIDDLEWARE.append("rollbar.contrib.django.middleware.RollbarNotifierMiddleware")

# Add build directory created by Create React App to serve webpage
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [os.path.join(BASE_DIR, "../", "frontend", "build")],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ]
        },
    }
]

if os.environ.get("DATABASE_URL"):
    DATABASES["default"] = dj_database_url.config(conn_max_age=600, ssl_require=True)

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/2.1/howto/static-files/

STATICFILES_DIRS = [os.path.join(BASE_DIR, "../", "frontend", "build", "static")]
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

WHITENOISE_ROOT = os.path.join(BASE_DIR, "../", "frontend", "build", "root")

ROLLBAR = {
    "access_token": ROLLBAR_TOKEN,
    "environment": ENVIRONMENT,
    "branch": "master",
    "root": BASE_DIR,
}
