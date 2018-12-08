from django.db import models
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

TEAM_NAMES = [
    'Richmond',
    'Carlton',
    'Melbourne',
    'Gold Coast',
    'Essendon',
    'Sydney',
    'Collingwood',
    'North Melbourne',
    'Adelaide',
    'Western Bulldogs',
    'Fremantle',
    'Port Adelaide',
    'St Kilda',
    'West Coast',
    'Brisbane',
    'Hawthorn',
    'GWS',
    'Geelong',
    'Fitzroy',
    'University'
]


def validate_name(name):
    if name not in TEAM_NAMES:
        raise ValidationError(
            _('%(name)s is not a valid team name'), params={'name': name}
        )


class Team(models.Model):
    name = models.CharField(
        max_length=100, unique=True, validators=[validate_name]
    )


class Match(models.Model):
    start_date_time = models.DateTimeField()
    round_number = models.PositiveSmallIntegerField()

    @property
    def winner(self):
        return max(self.teammatch_set.all(), key=lambda x: x.score).team

    @property
    def year(self):
        return self.start_date_time.year


class TeamMatch(models.Model):
    team = models.ForeignKey(Team, on_delete=models.CASCADE)
    match = models.ForeignKey(Match, on_delete=models.CASCADE)
    at_home = models.BooleanField()
    score = models.PositiveSmallIntegerField()


class MLModel(models.Model):
    trained_to_match = models.ForeignKey(
        Match, on_delete=models.SET_NULL, null=True, blank=True
    )
    name = models.CharField(max_length=100)
    description = models.TextField(null=True, blank=True)
    filepath = models.CharField(max_length=500, null=True, blank=True)


class Prediction(models.Model):
    match = models.ForeignKey(Match, on_delete=models.CASCADE)
    ml_model = models.ForeignKey(MLModel, on_delete=models.CASCADE)
    predicted_winner = models.ForeignKey(Team, on_delete=models.CASCADE)
    predicted_margin = models.SmallIntegerField()

    @property
    def is_correct(self):
        return self.predicted_winner == self.match.winner
