"""Data model for AFL matches."""

from __future__ import annotations
from typing import Optional, Union
from functools import reduce
from datetime import datetime, timedelta
from warnings import warn

from django.db import models, transaction
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
import pandas as pd

from server.types import FixtureData, MatchData
from .team import Team

# Rough estimate, but exactitude isn't necessary here
GAME_LENGTH_HRS = 3
WEEK_IN_DAYS = 7


def validate_is_utc(start_date_time: datetime) -> None:
    """Validate that start_date_time is always UTC for consistency."""
    if datetime.utcoffset(start_date_time) == timedelta(0):
        return None

    raise ValidationError(_("%(start_date_time)s is not set to the UTC"))


class Match(models.Model):
    """Data model for AFL matches."""

    start_date_time = models.DateTimeField(validators=[validate_is_utc])
    round_number = models.PositiveSmallIntegerField()
    venue = models.CharField(max_length=100, null=True, blank=True)
    winner = models.ForeignKey(Team, null=True, blank=True, on_delete=models.SET_NULL)
    margin = models.IntegerField(
        null=True, blank=True, validators=[MinValueValidator(0)]
    )

    class Meta:
        """Meta class for including more-advanced attributes & validations."""

        constraints = [
            models.UniqueConstraint(
                fields=["start_date_time", "venue"],
                name="unique_start_date_time_and_venue",
            )
        ]

    @classmethod
    def get_or_create_from_raw_data(
        cls, match_data: Union[FixtureData, MatchData]
    ) -> Match:
        """
        Get or create a match record from a row of raw match data.

        Params:
        -------
        match_data: A row of raw match data. Can be from fixture or match results data.

        Returns:
        --------
        A match record.
        """
        raw_date = (
            match_data["date"].to_pydatetime()
            if isinstance(match_data["date"], pd.Timestamp)
            else match_data["date"]
        )

        match_date = timezone.localtime(raw_date)

        with transaction.atomic():
            match, was_created = Match.objects.get_or_create(
                start_date_time=match_date,
                round_number=int(match_data["round_number"]),
                venue=match_data["venue"],
            )

            if was_created:
                match.full_clean()

        return match

    @classmethod
    def played_without_results(cls):
        """
        Get all matches that don't have any associated results data.

        Returns:
        --------
        A query set of past matches that haven't been updated with final scores yet.
        """
        return (
            cls.objects.prefetch_related("teammatch_set").filter(
                start_date_time__lt=timezone.localtime()
                - timedelta(hours=GAME_LENGTH_HRS),
                teammatch__score=0,
            )
            # Filtering by teammatch attributes returns duplicate matches
            # (one for each associated teammatch)
            .distinct("start_date_time", "venue")
        )

    @classmethod
    def earliest_date_time_without_results(cls) -> Optional[datetime]:
        """
        Get the earliest start_date_time of played matches without results.

        Returns:
        --------
        Date-time for the first past match without scores.
        """
        if not any(cls.played_without_results()):
            return None

        return cls.played_without_results().earliest("start_date_time").start_date_time

    @classmethod
    def update_results(cls, match_results: pd.DataFrame):
        """
        Fill in match results data for all matches that have been played.

        Params:
        -------
        match_results: Raw match results data.
        """
        for match in cls.played_without_results():
            match_result = match_results.query(
                "year == @match.year & "
                "round_number == @match.round_number & "
                "home_team == @match.team(at_home=True).name & "
                "away_team == @match.team(at_home=False).name"
            )

            match.update_result(match_result)

    def update_result(self, match_result: pd.DataFrame):
        """
        Fill in match results data for a match that's been played.

        Params:
        -------
        match_result: Raw data for a single match.
        """

        if not self.has_been_played or not self._validate_results_data_presence(
            match_result
        ):
            return None

        self._validate_one_result_row(match_result)

        for team_match in self.teammatch_set.all():
            team_match.update_score(match_result.iloc[0, :])

        self._save_result()

        for prediction in self.prediction_set.all():
            prediction.update_correctness()

        return None

    def _validate_results_data_presence(self, match_result: pd.DataFrame) -> bool:
        # AFLTables usually updates match results a few days after the round
        # is finished. Allowing for the occasional delay, we accept matches without
        # results data for a week before raising an error.
        if (
            self.start_date_time > timezone.localtime() - timedelta(days=WEEK_IN_DAYS)
            and not match_result.size
        ):
            warn(
                f"Unable to update the match between {self.team(at_home=True).name} "
                f"and {self.team(at_home=False).name} from round {self.round_number}. "
                "This is likely due to AFLTables not having updated the match results "
                "yet."
            )

            return False

        assert match_result.size, (
            "Didn't find any match data rows that matched match record:\n"
            "{\n"
            f"    start_date_time: {self.start_date_time},\n"
            f"    round_number: {self.round_number},\n"
            f"    venue: {self.venue},\n"
            f"    teammatch_set: {self.teammatch_set.values('team__name', 'at_home')}"
            "}"
        )

        return True

    @staticmethod
    def _validate_one_result_row(match_result: pd.DataFrame):
        assert len(match_result) == 1, (
            "Filtering match results by year, round_number and team name "
            "should result in a single row, but instead the following was "
            "returned:\n"
            f"{match_result}"
        )

    @property
    def is_draw(self):
        """Indicate whether a match result was a draw."""
        return self.has_results and reduce(
            lambda score_x, score_y: score_x == score_y, self._match_scores
        )

    @property
    def year(self):
        """Return the year in which the match is played."""
        return self.start_date_time.year

    def team(self, at_home: Optional[bool] = None) -> Team:
        """Return the record for the home or away team."""
        if at_home is None:
            raise ValueError("Must pass a boolean value for at_home")

        return self.teammatch_set.get(at_home=at_home).team

    @property
    def has_been_played(self):
        """Return whether a match has been played yet."""
        match_end_time = self.start_date_time + timedelta(hours=GAME_LENGTH_HRS)
        return match_end_time < timezone.localtime()

    @property
    def has_results(self):
        """Return whether a match has a final score."""
        return self.has_been_played and self._has_score

    @property
    def _has_score(self):
        return any([score > 0 for score in self._match_scores])

    @property
    def _match_scores(self):
        return self.teammatch_set.all().values_list("score", flat=True)

    def _save_result(self):
        self.margin = self._calculate_margin()
        self.winner = self._calculate_winner()
        self.full_clean()
        self.save()

    def _calculate_margin(self):
        if not self.has_been_played:
            return None

        return reduce(
            lambda score_x, score_y: abs(score_x - score_y), self._match_scores
        )

    def _calculate_winner(self):
        """Return the record for the winning team of the match."""
        if not self.has_been_played or self.is_draw:
            return None

        return max(self.teammatch_set.all(), key=lambda tm: tm.score).team
