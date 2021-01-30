"""Data model for AFL teams."""

from typing import List
import enum

from sqlalchemy import Column, String, Integer
from sqlalchemy.orm import validates

from tipping.models.base import ValidationError, Base


class TeamName(enum.Enum):
    """All VFL/AFL team names that have existed."""

    ADELAIDE = "Adelaide"
    BRISBANE = "Brisbane"
    CARLTON = "Carlton"
    COLLINGWOOD = "Collingwood"
    ESSENDON = "Essendon"
    FITZROY = "Fitzroy"
    FREMANTLE = "Fremantle"
    GEELONG = "Geelong"
    GOLD_COAST = "Gold Coast"
    GWS = "GWS"
    HAWTHORN = "Hawthorn"
    MELBOURNE = "Melbourne"
    NORTH_MELBOURNE = "North Melbourne"
    PORT_ADELAIDE = "Port Adelaide"
    RICHMOND = "Richmond"
    ST_KILDA = "St Kilda"
    SYDNEY = "Sydney"
    UNIVERSITY = "University"
    WESTERN_BULLDOGS = "Western Bulldogs"
    WEST_COAST = "West Coast"

    @classmethod
    def has_value(cls, name: str) -> bool:
        """Determines whether the given name is a TeamName value."""
        return name in cls.values()

    @classmethod
    def values(cls) -> List:
        """Returns all name values in TeamName."""
        return [member.value for member in cls]


class Team(Base):
    """Data model for AFL teams."""

    __tablename__ = "teams"

    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True)

    @validates("name")
    def validate_team_name(self, _key, name):
        """Validates that the name is in the TeamName enum."""
        if not TeamName.has_value(name):
            raise ValidationError(f"name {name} is not in {TeamName.values()}")

        return name
