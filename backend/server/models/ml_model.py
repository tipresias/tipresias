"""Data model for machine-learning models/estimators."""

from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError

from .match import Match


def validate_module_path(path: str) -> None:
    """Validate that the given path is for Python modules not files."""
    if "." in path and "/" not in path:
        return None

    raise ValidationError(
        _(
            "%(path)s is not a valid module path. Be sure to separate modules & classes "
            "with a '.'"
        ),
        params={"path": path},
    )


class MLModel(models.Model):
    """Data model for machine-learning models/estimators."""

    trained_to_match = models.ForeignKey(
        Match, on_delete=models.SET_NULL, null=True, blank=True
    )
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(null=True, blank=True)
    filepath = models.CharField(max_length=500, null=True, blank=True)
    data_class_path = models.CharField(
        max_length=500, null=True, blank=True, validators=[validate_module_path]
    )
