import os
from datetime import timezone, timedelta

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__)))
DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../", "data"))

HOURS_FROM_UTC_TO_MELBOURNE = 11
MELBOURNE_TIMEZONE = timezone(timedelta(hours=HOURS_FROM_UTC_TO_MELBOURNE))
