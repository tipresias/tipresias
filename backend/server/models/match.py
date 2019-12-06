"""Data model for AFL matches"""

from typing import Optional
from functools import reduce
from datetime import datetime, timedelta

from django.db import models
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from django.utils import timezone

from .team import Team

# Rough estimate, but exactitude isn't necessary here
GAME_LENGTH_HRS = 3


def validate_is_utc(start_date_time: datetime) -> None:
    if datetime.utcoffset(start_date_time) == timedelta(0):
        return None

    raise ValidationError(_("%(start_date_time)s is not set to the UTC"))


class Match(models.Model):
    """Data model for AFL matches"""

    start_date_time = models.DateTimeField(validators=[validate_is_utc])
    round_number = models.PositiveSmallIntegerField()
    venue = models.CharField(max_length=100, null=True, blank=True)

    class Meta:
        unique_together = ("start_date_time", "venue")

    @property
    def is_draw(self):
        return self.has_been_played and reduce(
            lambda score_x, score_y: score_x == score_y, self.__match_scores
        )

    @property
    def winner(self):
        if not self.has_been_played or self.is_draw:
            return None

        return max(self.teammatch_set.all(), key=lambda tm: tm.score).team

    @property
    def margin(self):
        if not self.has_been_played:
            return 0

        return reduce(
            lambda score_x, score_y: abs(score_x - score_y), self.__match_scores
        )

    @property
    def year(self):
        return self.start_date_time.year

    def team(self, at_home: Optional[bool] = None) -> Team:
        if at_home is None:
            raise ValueError("Must pass a boolean value for at_home")

        return self.teammatch_set.get(at_home=at_home).team

    @property
    def has_been_played(self):
        match_end_time = self.start_date_time + timedelta(hours=GAME_LENGTH_HRS)

        # We need to check the scores in case the data hasn't been updated since the
        # match was played, because as far as the data is concerned it hasn't, even though
        # the date has passed.
        return self.__has_score and match_end_time < timezone.localtime()

    @property
    def __has_score(self):
        return any([score > 0 for score in self.__match_scores])

    @property
    def __match_scores(self):
        return self.teammatch_set.all().values_list("score", flat=True)
