import os
from datetime import datetime
from typing import List, Union
import pytz

from django.core.management.base import BaseCommand
from django.template.loader import get_template
import sendgrid
from sendgrid.helpers.mail import Mail

from server.models import Match, Prediction

JAN = 1
FIRST = 1
EMAIL_FROM = "tipresias@tipresias.com"
PREDICTION_HEADERS = [
    "Date",
    "Home Team",
    "Away Team",
    "Predicted Winner",
    "Predicted Margin",
]


class Command(BaseCommand):
    """
    manage.py command for 'send_email' that sends an email with the most recent predictions
    AFL matches
    """

    help = """
    Send email with predictions for most-recent round predicted (either the upcoming round
    or most recently-played round).
    """

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

    def handle(self, *_args, **_kwargs):
        """Run 'send_email' command"""

        right_now = datetime.now(tz=pytz.UTC)
        upcoming_match = Match.objects.filter(start_date_time__gt=right_now).earliest(
            "start_date_time"
        )
        upcoming_match_year = upcoming_match.start_date_time.year
        upcoming_round = upcoming_match.round_number

        upcoming_round_predictions = (
            Prediction.objects.filter(
                ml_model__name="tipresias",
                match__start_date_time__gt=datetime(
                    upcoming_match_year, JAN, FIRST, tzinfo=pytz.UTC
                ),
                match__round_number=upcoming_round,
            )
            .select_related("match")
            .prefetch_related("match__teammatch_set")
            .order_by("match__start_date_time")
        )

        prediction_rows = [
            self.__map_prediction_to_row(prediction)
            for prediction in upcoming_round_predictions
        ]

        self.__send_tips_email(prediction_rows, upcoming_round)

    @staticmethod
    def __map_prediction_to_row(prediction: Prediction) -> List[Union[str, int]]:
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

    @staticmethod
    def __send_tips_email(
        prediction_rows: List[Union[str, int]], latest_round: int
    ) -> None:
        prediction_mail_params = {
            "prediction_headers": PREDICTION_HEADERS,
            "prediction_rows": prediction_rows,
            "round_number": latest_round,
        }

        email_template = get_template("tip_mail.html")
        email_body = email_template.render(prediction_mail_params)

        email_recipient = os.environ.get("EMAIL_RECIPIENT")
        api_key = os.environ.get("SENDGRID_API_KEY")

        if email_recipient is None:
            raise ValueError(
                "No email recipient was defined. Be sure to define the environment variable "
                "'EMAIL_RECIPIENT' in order to send tips emails."
            )

        if api_key is None:
            raise ValueError(
                "The Sendgrid API key wasn't defined. Be sure to define the environment variable "
                "'SENDGRID_API_KEY' in order to send tips emails."
            )

        mail = Mail(
            from_email=EMAIL_FROM,
            to_emails=email_recipient,
            subject=f"Footy Tips for Round {latest_round}",
            html_content=email_body,
        )

        sendgrid.SendGridAPIClient(api_key).send(mail)
