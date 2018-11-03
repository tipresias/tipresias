# pylint: disable=W0401,W0614
from project.settings.common import *

DEBUG = False

SECRET_KEY = os.environ.get('SECRET_KEY')
