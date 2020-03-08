"""Data model for AFL teams."""

from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _


def validate_name(name: str) -> None:
    """Validate that the given name is for a real team."""
    if name in settings.TEAM_NAMES:
        return None

    raise ValidationError(_("%(name)s is not a valid team name"), params={"name": name})


class Team(models.Model):
    """Data model for AFL teams."""

    name = models.CharField(max_length=100, unique=True, validators=[validate_name])
