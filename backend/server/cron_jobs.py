"""Cron jobs to be run in production"""

from django_cron import CronJobBase, Schedule

MINUTES_PER_HOUR = 60


class SendTips(CronJobBase):
    """Cron job for running the 'tip' and 'send_email' management commands"""

    # Running at noon to get reasonably up-to-date betting/roster data while giving me
    # plenty of time to submit my tips.
    RUN_AT_TIMES = ["12:00"]

    schedule = Schedule(run_every_mins=RUN_EVERY_MINS)
    code = "tipresias.send_tips"

    def do(self):
        pass
