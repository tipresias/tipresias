import os

# pylint: disable=W0401,W0614
from project.settings.common import *

ALLOWED_HOSTS = ["backend", "localhost"]

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = "^6&#7de5dx#eqg6dm^l3#@wj6vjjn%2f=u(!&ia()h-l1ppan!"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": "tipresias",
        "HOST": os.getenv("DATABASE_HOST"),
        "USER": "postgres",
        "PASSWORD": "",
        "PORT": 5432,
    }
}
