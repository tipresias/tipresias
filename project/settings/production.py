# pylint: disable=W0401,W0614
from project.settings.common import *

DEBUG = False

SECRET_KEY = os.environ.get('SECRET_KEY')

INSTALLED_APPS.extend([
    'whitenoise.runserver_nostatic',
    'django.contrib.staticfiles',
])

# Must insert after SecurityMiddleware, which is first in settings/common.py
MIDDLEWARE.insert(1, 'whitenoise.middleware.WhiteNoiseMiddleware')

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [
            os.path.join(BASE_DIR, 'client', 'build')
        ],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/2.1/howto/static-files/

STATICFILES_DIRS = [
    os.path.join(BASE_DIR, 'client', 'build', 'static'),
]
STATICFILES_STORAGE = (
    'whitenoise.storage.CompressedManifestStaticFilesStorage'
)
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATIC_URL = '/static/'
WHITENOISE_ROOT = os.path.join(BASE_DIR, 'client', 'build', 'root')
