from functools import reduce
from datetime import datetime, timezone, timedelta
from django.db import models
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

TEAM_NAMES = [
    "Richmond",
    "Carlton",
    "Melbourne",
    "Gold Coast",
    "Essendon",
    "Sydney",
    "Collingwood",
    "North Melbourne",
    "Adelaide",
    "Western Bulldogs",
    "Fremantle",
    "Port Adelaide",
    "St Kilda",
    "West Coast",
    "Brisbane",
    "Hawthorn",
    "GWS",
    "Geelong",
    "Fitzroy",
    "University",
]
# Rough estimate, but exactitude isn't necessary here
GAME_LENGTH_HRS = 3


def validate_name(name: str) -> None:
    if name in TEAM_NAMES:
        return None

    raise ValidationError(_("%(name)s is not a valid team name"), params={"name": name})


def validate_module_path(path: str) -> None:
    if "." in path and "/" not in path:
        return None

    raise ValidationError(
        _(
            "%(path)s is not a valid module path. Be sure to separate modules & classes "
            "with a '.'"
        ),
        params={"path": path},
    )


class Team(models.Model):
    name = models.CharField(max_length=100, unique=True, validators=[validate_name])


class Match(models.Model):
    start_date_time = models.DateTimeField()
    round_number = models.PositiveSmallIntegerField()
    venue = models.CharField(max_length=100, null=True, blank=True)

    class Meta:
        unique_together = ("start_date_time", "venue")

    @property
    def is_draw(self):
        return self.has_been_played and reduce(
            lambda x, y: x.score == y.score, self.teammatch_set.all()
        )

    @property
    def winner(self):
        if not self.has_been_played or self.is_draw:
            return None

        return max(self.teammatch_set.all(), key=lambda x: x.score).team

    @property
    def year(self):
        return self.start_date_time.year

    @property
    def has_been_played(self):
        # We need to check the scores in case the data hasn't been updated since the
        # match was played, because as far as the data is concerned it hasn't, even though
        # the date has passed.
        return self.__has_score and (
            self.start_date_time
            < datetime.now(timezone.utc) - timedelta(hours=GAME_LENGTH_HRS)
        )

    @property
    def __has_score(self):
        return any(
            [
                score > 0
                for score in self.teammatch_set.all().values_list("score", flat=True)
            ]
        )


class TeamMatch(models.Model):
    team = models.ForeignKey(Team, on_delete=models.CASCADE)
    match = models.ForeignKey(Match, on_delete=models.CASCADE)
    at_home = models.BooleanField()
    score = models.PositiveSmallIntegerField(default=0)


class MLModel(models.Model):
    trained_to_match = models.ForeignKey(
        Match, on_delete=models.SET_NULL, null=True, blank=True
    )
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(null=True, blank=True)
    filepath = models.CharField(max_length=500, null=True, blank=True)
    data_class_path = models.CharField(
        max_length=500, null=True, blank=True, validators=[validate_module_path]
    )


class Prediction(models.Model):
    match = models.ForeignKey(Match, on_delete=models.CASCADE)
    ml_model = models.ForeignKey(MLModel, on_delete=models.CASCADE)
    predicted_winner = models.ForeignKey(Team, on_delete=models.CASCADE)
    predicted_margin = models.PositiveSmallIntegerField()

    @property
    def is_correct(self):
        return self.match.has_been_played and (
            self.match.is_draw or self.predicted_winner == self.match.winner
        )
