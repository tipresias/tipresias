"""Data model for machine-learning models/estimators."""

from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError


class PredictionType(models.TextChoices):
    """
    Enum for different prediction types.

    Correspond to 'predicted_<prediction type>' fields on the Prediction model.
    """

    MARGIN = _("Margin")
    WIN_PROBABILITY = _("Win Probability")


class MLModel(models.Model):
    """
    Data model for machine-learning models/estimators.

    Attributes:
    -----------
    name: Name of the model.
    description: Optional description to provide more information about the model.
    is_principal: Whether the model's predicted winners represent the official
        predicted winners of Tipresias.
    used_in_competitions: Whether the model's predictions are submitted for competitions.
    """

    class Meta:
        """Meta class for including more-advanced attributes & validations."""

        constraints = [
            models.UniqueConstraint(
                fields=["is_principal"],
                condition=models.Q(is_principal=True),
                name="one_principal_model",
            ),
            # This isn't a hard rule, but the assumption of this constraint is built
            # into some model-selection logic, and it doesn't make much sense
            # to have two different models making the same type of prediction
            # for competitions; might as well just use whichever is better.
            models.UniqueConstraint(
                fields=["prediction_type"],
                condition=models.Q(used_in_competitions=True),
                name="unique_prediction_type_for_competitions",
            ),
        ]

    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(null=True, blank=True)
    is_principal = models.BooleanField(default=False)
    used_in_competitions = models.BooleanField(default=False)
    prediction_type = models.CharField(
        max_length=100,
        choices=PredictionType.choices,
        # The default is somewhat arbitrary to avoid permitting null values,
        # but MARGIN is the most common prediciton type for now.
        default=PredictionType.MARGIN,
    )

    def clean(self):
        """Perform field cleaning and model validation."""

        if self.is_principal and not self.used_in_competitions:
            raise ValidationError(_("A principal model must be used for competitions."))
