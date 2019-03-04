from datetime import datetime, timezone

from django.core.management.base import BaseCommand

from server.models import Match, Prediction

JAN = 1
FIRST = 1


class Command(BaseCommand):
    """
    manage.py command for 'send_email' that sends an email with the most recent predictions AFL matches
    """

    help = """
    Send email with predictions for most-recent round predicted (either the upcoming round
    or most recently-played round).
    """

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

    def handle(self, *_args, **_kwargs):
        """Run 'send_email' command"""

        latest_match = Match.objects.latest("start_date_time")
        latest_year = latest_match.start_date_time.year
        latest_round = latest_match.round_number

        latest_round_predictions = (
            Prediction.objects.filter(
                ml_model__name="tipresias",
                match__start_date_time__gt=datetime(
                    latest_year, JAN, FIRST, tzinfo=timezone.utc
                ),
                match__round_number=latest_round,
            )
            .select_related("match")
            .prefetch_related("match__teammatch_set")
            .order_by("match__start_date_time")
        )

        prediction_headers = [
            ["date", "home_team", "away_team", "predicted_winner", "predicted_margin"]
        ]
        prediction_rows = [
            self.__map_prediction_to_row(prediction)
            for prediction in latest_round_predictions
        ]
        prediction_table = prediction_headers + prediction_rows

    @staticmethod
    def __map_prediction_to_row(prediction: Prediction):
        match = prediction.match
        home_team = match.teammatch_set.get(at_home=True).team.name
        away_team = match.teammatch_set.get(at_home=False).team.name

        return [
            str(match.start_date_time),
            home_team,
            away_team,
            prediction.predicted_winner.name,
            prediction.predicted_margin,
        ]
