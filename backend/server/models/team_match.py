"""Data model for the join table for matches and teams."""

from __future__ import annotations
from typing import Type, TypeVar, Union, Tuple, Dict

from django.db import models, transaction
import pandas as pd

from server.types import FixtureData, MatchData
from .team import Team
from .match import Match


T = TypeVar("T", bound="TeamMatch")


NO_SCORE = 0


class TeamMatchCollection:
    """Collection of team records that can trigger further DB queries."""

    def __init__(self, team_matches: models.QuerySet):
        self.team_matches = team_matches

    def __len__(self):
        return len(self.team_matches)

    def __iter__(self):
        return (team for team in self.team_matches)

    def delete(self) -> Tuple[int, Dict[str, int]]:
        """Delete all team match records in the collection."""
        return self.team_matches.delete()

    def count(self) -> int:
        """
        Get the number of team match records in the collection.

        Returns:
        --------
        Count of team match records.
        """
        return self.team_matches.count()

    def order_by(self, ordering_attribute: str) -> TeamMatchCollection:
        """
        Order the collection elements by the given attribute(s).

        Params:
        -------
        ordering_attribute: Name of the attribute. Optionally prepend '-'
            to sort in descending order.

        Returns:
        --------
        Sorted team match collection.
        """
        return self.team_matches.order_by(ordering_attribute)

    def update(self, **attributes) -> TeamMatchCollection:
        """
        Update all TeamMatch records in the collection with the given attribute values.

        Params:
        -------
        attributes: TeamMatch attribute values to update.

        Returns:
        --------
        Count of updated records.
        """
        return self.team_matches.update(**attributes)


class TeamMatch(models.Model):
    """Data model for the join table for matches and teams."""

    team = models.ForeignKey(Team, on_delete=models.CASCADE)
    match = models.ForeignKey(Match, on_delete=models.CASCADE)
    at_home = models.BooleanField()
    score = models.PositiveSmallIntegerField(default=0)

    @classmethod
    def create(cls, **attributes) -> Team:
        """
        Create a TeamMatch record in the database.

        Params:
        -------
        attributes: TeamMatch attributes for the created record.

        Returns:
        --------
        An instance of the created team match.
        """
        return cls.objects.create(**attributes)

    @classmethod
    def count(cls) -> int:
        """
        Get the number of TeamMatch records in the database.

        Returns:
        --------
        Count of team match records.
        """
        return cls.objects.count()

    @classmethod
    def get(cls, **attributes) -> Team:
        """
        Get a TeamMatch record that matches the given attributes from the database.

        Params:
        -------
        attributes: TeamMatch attributes for the created record.

        Returns:
        --------
        The requested team match record.
        """
        return cls.objects.get(**attributes)

    @classmethod
    def get_or_create(cls, **attributes) -> Tuple[Team, bool]:
        """
        Get a TeamMatch record that matches the given attributes or create it if missing.

        Params:
        -------
        attributes: TeamMatch attributes for the requested/created record.

        Returns:
        --------
        The requested team match record and whether it was created.
        """
        return cls.objects.get_or_create(**attributes)

    @classmethod
    def all(cls) -> TeamMatchCollection:
        """
        Get all TeamMatch records from the database.

        Returns:
        --------
        A list of team match records.
        """
        return TeamMatchCollection(cls.objects.all())

    @classmethod
    def filter(cls, **attributes) -> TeamMatchCollection:
        """
        Get all TeamMatch records that match the given filter values.

        Params:
        -------
        attributes: TeamMatch attributes to filter by.

        Returns:
        --------
        A list of team match records.
        """
        return TeamMatchCollection(cls.objects.filter(**attributes))

    @classmethod
    def get_or_create_from_raw_data(
        cls: Type[T], match: Match, match_data: Union[FixtureData, MatchData]
    ) -> Tuple[T, T]:
        """
        Get or create a pair of team-match records associated with a given match.

        Params:
        -------
        match: A match record from the DB.
        match_data: A row of raw match data.

        Returns:
        --------
        A pair of team-match records.
        """
        teammatch_set = match.teammatch_set
        team_match_count = teammatch_set.count()

        if team_match_count == 2:
            team_match_names = set(teammatch_set.values_list("team__name", flat=True))
            data_names = set([match_data["home_team"], match_data["away_team"]])

            assert team_match_names & data_names == team_match_names, (
                f"Team names in the teammatch_set ({team_match_names}) associated with "
                "{match} need to be the same as the given match data ({data_names})."
            )

            return teammatch_set.first(), teammatch_set.last()

        assert team_match_count == 0, (
            f"{match} has {team_match_count} associated TeamMatches, "
            "which shouldn't happen. Figure out what's up."
        )

        with transaction.atomic():
            team_matches: Tuple[T, T] = (
                cls._create_from_raw_data(match, match_data, True),
                cls._create_from_raw_data(match, match_data, False),
            )

        return team_matches

    @classmethod
    def _create_from_raw_data(cls, match: Match, match_data, at_home: bool) -> T:
        team_prefix = "home" if at_home else "away"
        team_name = match_data[f"{team_prefix}_team"]
        team, _was_created = Team.get_or_create(name=team_name)

        team_score = match_data.get(f"{team_prefix}_score", 0)
        team_match = TeamMatch(
            team=team, match=match, at_home=at_home, score=team_score
        )

        team_match.full_clean()
        team_match.save()

        return team_match

    def update_score(self, match_result: pd.Series):
        """
        Update the final scores for match records.

        Params:
        -------
        match_result: A row of raw match data with final scores.
        """
        team_type_prefix = "home" if self.at_home else "away"

        assert self.team.name == match_result[f"{team_type_prefix}_team"]

        self.score = match_result[f"{team_type_prefix}_score"]
        self.full_clean()
        self.save()
