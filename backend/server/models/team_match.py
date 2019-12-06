"""Data model for the join table for matches and teams"""

from django.db import models

from .team import Team
from .match import Match


class TeamMatch(models.Model):
    """Data model for the join table for matches and teams"""

    team = models.ForeignKey(Team, on_delete=models.CASCADE)
    match = models.ForeignKey(Match, on_delete=models.CASCADE)
    at_home = models.BooleanField()
    score = models.PositiveSmallIntegerField(default=0)
