"""Data model for AFL teams."""

from typing import Any
import enum

from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Enum, Integer


# mypy doesn't play nice with dynamic base classes, so we just call it Any
Base: Any = declarative_base()


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


class Team(Base):
    """Data model for AFL teams."""

    __tablename__ = "teams"

    id = Column(Integer, primary_key=True)
    name = Column(Enum(TeamName))
