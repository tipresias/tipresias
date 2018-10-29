from django.db import models


class Team(models.Model):
    name = models.CharField(max_length=100)


class Match(models.Model):
    start_date_time = models.DateTimeField()
    round_number = models.PositiveSmallIntegerField()

    year = start_date_time.year


class TeamMatch(models.Model):
    team = models.ForeignKey(Team, on_delete=models.CASCADE)
    match = models.ForeignKey(Match, on_delete=models.CASCADE)
    at_home = models.BooleanField()
    score = models.PositiveSmallIntegerField()


class MLModel(models.Model):
    trained_to_match = models.ForeignKey(
        Match, on_delete=models.SET_NULL, null=True
    )
    name = models.CharField(max_length=100)
    description = models.TextField()
    filepath = models.CharField(max_length=500)


class Prediction(models.Model):
    match = models.ForeignKey(Match, on_delete=models.CASCADE)
    ml_model = models.ForeignKey(MLModel, on_delete=models.CASCADE)
    predicted_winner = models.ForeignKey(Team, on_delete=models.CASCADE)
    predicted_margin = models.SmallIntegerField()
