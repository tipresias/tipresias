"""Data model for machine-learning models/estimators."""

from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError


class MLModel(models.Model):
    """Data model for machine-learning models/estimators."""

    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(null=True, blank=True)
