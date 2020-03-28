"""
Script for dumping filtered DB data per Django's dumpdata.

This is intended as a one-time script, so filters are hard-coded. We can add arguments
later if this gets more use.
"""

from typing import Dict, Any, List, Union
import os
import sys
import json
from datetime import date, datetime

import django
from django.db.models import Model, Q
from django.conf import settings
from mypy_extensions import TypedDict

PROJECT_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "../"))

if PROJECT_PATH not in sys.path:
    sys.path.append(PROJECT_PATH)

django.setup()

from server.models import Prediction  # pylint: disable=wrong-import-position


DumpRecord = TypedDict(
    "DumpRecord", {"model": str, "pk": int, "fields": Dict[str, Any]}
)


APP_NAME = "server"


def _clean_value(value: Any) -> Union[str, int, float]:
    if type(value) in [datetime, date]:  # pylint: disable=unidiomatic-typecheck
        return str(value)

    return value


def _reshape_record_fields(model_name: str, record: Dict[str, Any]) -> DumpRecord:
    fields = {k: _clean_value(v) for k, v in record.items() if k != "id"}

    return {"model": APP_NAME + "." + model_name, "pk": record["id"], "fields": fields}


def _get_fields_for(model_class: Model) -> List[str]:
    return [
        field.attname
        for field in model_class._meta.get_fields()  # pylint: disable=protected-access
        # Association fields appear in list, but aren't attributes
        # unless the given record has the foreign key.
        if hasattr(field, "attname")
    ]


def main():
    """Dump filtered DB data per Django's dumpdata."""
    season_2019_preds_for_tipresias_2020 = Q(ml_model__name="tipresias_2020") & Q(
        match__start_date_time__year=2019
    )
    season_2020_preds_for_round_1 = Q(match__start_date_time__year=2020) & (
        Q(match__round_number=1)
    )

    prediction_records = Prediction.objects.filter(
        season_2019_preds_for_tipresias_2020 | season_2020_preds_for_round_1
    ).values(*_get_fields_for(Prediction))

    prediction_dump = [
        _reshape_record_fields("prediction", record) for record in prediction_records
    ]
    dump_filepath = os.path.join(
        settings.BASE_DIR, APP_NAME, "fixtures", f"{date.today()}-prediction-dump.json",
    )

    with open(dump_filepath, "w") as file:
        json.dump(prediction_dump, file, indent=2)


if __name__ == "__main__":
    main()
