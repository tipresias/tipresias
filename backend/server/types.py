from datetime import datetime
from mypy_extensions import TypedDict

FixtureData = TypedDict(
    "FixtureData",
    {
        "date": datetime,
        "season": int,
        "round": int,
        "round_label": str,
        "crowd": int,
        "home_team": str,
        "away_team": str,
        "home_score": int,
        "away_score": int,
        "venue": str,
    },
)
