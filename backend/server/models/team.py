"""Data model for AFL teams."""

from __future__ import annotations
from typing import Tuple, Dict

from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from mypy_extensions import TypedDict


TeamRecord = TypedDict("TeamRecord", {"name": str, "id": int})


class TeamCollection:
    """Collection of team records that can trigger further DB queries."""

    def __init__(self, teams: models.QuerySet):
        self.teams = teams

    def __len__(self):
        return len(self.teams)

    def __iter__(self):
        return (team for team in self.teams)

    def delete(self) -> Tuple[int, Dict[str, int]]:
        """Delete all team records in the collection."""
        return self.teams.delete()


def validate_name(name: str) -> None:
    """Validate that the given name is for a real team."""
    if name in settings.TEAM_NAMES:
        return None

    raise ValidationError(_("%(name)s is not a valid team name"), params={"name": name})


class Team(models.Model):
    """Data model for AFL teams."""

    name = models.CharField(max_length=100, unique=True, validators=[validate_name])

    @classmethod
    def create(cls, **attributes) -> Team:
        """
        Create a Team record in the database.

        Params:
        -------
        attributes: Team attributes for the created record.

        Returns:
        --------
        An instance of the created team.
        """
        return cls.objects.create(**attributes)

    @classmethod
    def count(cls) -> int:
        """
        Get the number of Team records in the database.

        Returns:
        --------
        Count of team records.
        """
        return cls.objects.count()

    @classmethod
    def get(cls, **attributes) -> Team:
        """
        Get a Team record that matches the given attributes from the database.

        Params:
        -------
        attributes: Team attributes for the created record.

        Returns:
        --------
        The requested team record.
        """
        return cls.objects.get(**attributes)

    @classmethod
    def get_or_create(cls, **attributes) -> Tuple[Team, bool]:
        """
        Get a Team record that matches the given attributes or create it if missing.

        Params:
        -------
        attributes: Team attributes for the requested/created record.

        Returns:
        --------
        The requested team record and whether it was created.
        """
        return cls.objects.get_or_create(**attributes)

    @classmethod
    def all(cls) -> TeamCollection:
        """
        Get all Team records from the database.

        Returns:
        --------
        A list of team records.
        """
        return TeamCollection(cls.objects.all())
