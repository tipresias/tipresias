"""Cron jobs to be run in production"""

from datetime import datetime
from django_cron import CronJobBase, Schedule
import pandas as pd

# TODO: These commands need to be refactored, then the refactored classes/functions
# used in this cron job, but I want to get something working, so I'm gonna be lazy
from server.management.commands import tip, send_email
from machine_learning.data_import import FootywireDataImporter
from project.settings.common import MELBOURNE_TIMEZONE

# Note that Python starts weeks on Monday (index = 0) and ends them on Sunday
# (index = 6)
SATURDAY = 5
MELBOURNE_TIMEZONE_NAME = "Australia/Melbourne"


class SendTips(CronJobBase):
    """Cron job for running the 'tip' and 'send_email' management commands"""

    # Running at noon to get reasonably up-to-date betting/roster data while giving me
    # plenty of time to submit my tips.
    RUN_AT_TIMES = ["12:00"]

    schedule = Schedule(run_at_times=RUN_AT_TIMES)
    code = "tipresias.send_tips"

    def __init__(self, data_reader=FootywireDataImporter()):
        super().__init__()

        # TODO: Need to set server timezone to Melbourne time for this to work as
        # intended
        self.right_now = datetime.now(tz=MELBOURNE_TIMEZONE)
        self.data_reader = data_reader

    def do(self):
        fixture_data_frame = self.__fetch_fixture_data(self.right_now.year)
        fixture_dates = fixture_data_frame["date"].dt.date
        is_before_saturday = self.right_now.date().weekday() < SATURDAY

        # This is to make sure that we have roster data for tips, because for rounds
        # Thursday games, we have to tip on Thursday before rosters are announced for
        # the rest of the matches (they usually get announced on Thursday around
        # 6:30 pm). So, we'll want to update tips for the rest of the round on Friday.
        if self.__is_match_today(fixture_dates) and is_before_saturday:
            tip.Command().handle()
            send_email.Command().handle()

    def __fetch_fixture_data(self, year: int) -> pd.DataFrame:
        fixture_data_frame = self.data_reader.get_fixture(
            year_range=(year, year + 1), fetch_data=True
        ).assign(date=lambda df: df["date"].dt.tz_localize(MELBOURNE_TIMEZONE))

        latest_match_datetime = fixture_data_frame["date"].max()

        if self.right_now > latest_match_datetime:
            print(
                f"No unplayed matches found in {year}. We will try to fetch "
                f"fixture for {year + 1}.\n"
            )

            fixture_data_frame = self.data_reader.get_fixture(
                year_range=(year, year + 1), fetch_data=True
            ).assign(date=lambda df: df["date"].dt.tz_localize(MELBOURNE_TIMEZONE))

            latest_match_datetime = fixture_data_frame["date"].max()

            if self.right_now > latest_match_datetime:
                raise ValueError(
                    f"No unplayed matches found in {year + 1}, and we're not going "
                    "to keep trying. Please try a season that hasn't been completed.\n"
                )

        return fixture_data_frame

    def __is_match_today(self, fixture_dates: pd.Series) -> bool:
        return (fixture_dates == self.right_now.date()).any()
