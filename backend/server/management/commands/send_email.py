"""Django command for sending predictions via email."""

import os
from datetime import datetime
from typing import List, Union

from django.core.management.base import BaseCommand
from django.template.loader import get_template
from django.utils import timezone
import sendgrid
from sendgrid.helpers.mail import Mail

from server.models import Match
from server.models.ml_model import PredictionType

JAN = 1
FIRST = 1
EMAIL_FROM = "tipresias@tipresias.com"
PREDICTION_HEADERS = [
    "Date",
    "Home Team",
    "Away Team",
    "Predicted Winner",
    "Predicted Margin",
    "Predicted Win Probability",
    "Probability Predicts Different Team",
]


class Command(BaseCommand):
    """Django command that sends an email with predictions for upcoming AFL matches."""

    help = """
    Send email with predictions for most-recent round predicted
    (either the upcoming round or most recently-played round).
    """

    def handle(self, *_args, **_kwargs):
        """Run 'send_email' command."""
        right_now = timezone.localtime()
        future_matches = Match.objects.filter(start_date_time__gt=right_now)

        if future_matches.count() == 0:
            return None

        upcoming_match = future_matches.earliest("start_date_time")
        upcoming_match_year = upcoming_match.start_date_time.year
        upcoming_round = upcoming_match.round_number

        upcoming_matches = (
            Match.objects.filter(
                start_date_time__gt=timezone.make_aware(
                    datetime(upcoming_match_year, JAN, FIRST)
                ),
                round_number=upcoming_round,
            )
            .prefetch_related("teammatch_set", "prediction_set")
            .order_by("start_date_time")
        )

        prediction_rows = [
            self.__map_prediction_to_row(match) for match in upcoming_matches
        ]

        self.__send_tips_email(prediction_rows, upcoming_round)

        return None

    @staticmethod
    def __map_prediction_to_row(match: Match) -> List[Union[str, int]]:
        home_team = match.teammatch_set.get(at_home=True).team.name
        away_team = match.teammatch_set.get(at_home=False).team.name

        match_predictions = match.prediction_set.filter(
            ml_model__used_in_competitions=True
        )

        margin_prediction = match_predictions.get(
            ml_model__prediction_type=PredictionType.MARGIN,
        )
        probability_prediction = match_predictions.get(
            ml_model__prediction_type=PredictionType.WIN_PROBABILITY,
        )

        principle_predicted_winner = match_predictions.get(
            ml_model__is_principle=True
        ).predicted_winner.name
        secondary_predicted_winner = match_predictions.get(
            ml_model__is_principle=False
        ).predicted_winner.name

        different_winner_label = (
            ""
            if principle_predicted_winner == secondary_predicted_winner
            else secondary_predicted_winner
        )

        display_predicted_margin = round(margin_prediction.predicted_margin, 2)
        display_predicted_win_probability = (
            str(round(probability_prediction.predicted_win_probability * 100, 2)) + "%"
        )

        return [
            str(match.start_date_time),
            home_team,
            away_team,
            principle_predicted_winner,
            display_predicted_margin,
            display_predicted_win_probability,
            different_winner_label,
        ]

    @staticmethod
    def __send_tips_email(
        prediction_rows: List[List[Union[str, int]]], latest_round: int
    ) -> None:
        assert len(PREDICTION_HEADERS) == len(prediction_rows[0])

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
