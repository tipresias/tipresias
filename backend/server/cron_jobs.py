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
MINS_PER_12_HOURS = 60 * 12


class SendTips(CronJobBase):
    """Cron job for running the 'tip' and 'send_email' management commands"""

    schedule = Schedule(run_every_mins=MINS_PER_12_HOURS)
    code = "tipresias.send_tips"

    def __init__(self, verbose=1, data_reader=FootywireDataImporter()):
        super().__init__()

        self.verbose = verbose
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
        if not self.__is_match_today(fixture_dates):
            if self.verbose == 1:
                print(
                    f"{str(self.right_now)} There is no match today, so it's unlikely "
                    "that all necessary data is available for making predictions"
                )
            return None

        if not is_before_saturday:
            if self.verbose == 1:
                print(
                    f"{str(self.right_now)} It is after Friday, so the latest tips "
                    "should include all necessary data and don't need to be updated"
                )
            return None

        tip.Command(verbose=0).handle()
        send_email.Command(verbose=0).handle()
        print(f"{self.right_now} Updated tips and sent email")
        return None

    def __fetch_fixture_data(self, year: int) -> pd.DataFrame:
        fixture_data_frame = self.data_reader.get_fixture(
            year_range=(year, year + 1), fetch_data=True
        ).assign(date=lambda df: df["date"].dt.tz_localize(MELBOURNE_TIMEZONE))

        latest_match_datetime = fixture_data_frame["date"].max()

        if self.right_now > latest_match_datetime:
            if self.verbose == 1:
                print(
                    f"{self.right_now} No unplayed matches found in {year}. "
                    f"We will try to fetch fixture for {year + 1}.\n"
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
