"""Shared functionality for model classes."""

from typing import Any
from sqlalchemy.ext.declarative import declarative_base


# mypy doesn't play nice with dynamic base classes, so we just call it Any
Base: Any = declarative_base()


class ValidationError(Exception):
    """Error for failed validation checks."""
