import os
from datetime import timezone, timedelta
import yaml


BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../"))
DATA_DIR = os.path.join(BASE_DIR, "data/01_raw/")

HOURS_FROM_UTC_TO_MELBOURNE = 11
MELBOURNE_TIMEZONE = timezone(timedelta(hours=HOURS_FROM_UTC_TO_MELBOURNE))

with open(os.path.join(BASE_DIR, "src/machine_learning/ml_models.yml"), "r") as file:
    ML_MODELS = yaml.safe_load(file).get("models", [])
