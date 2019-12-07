"""Data model for the join table for matches and teams"""

from typing import Type, TypeVar, Union, Tuple, cast, List
from django.db import models, transaction

from server.types import CleanFixtureData, MatchData
from .team import Team
from .match import Match


T = TypeVar("T", bound="TeamMatch")


NO_SCORE = 0


class TeamMatch(models.Model):
    """Data model for the join table for matches and teams"""

    team = models.ForeignKey(Team, on_delete=models.CASCADE)
    match = models.ForeignKey(Match, on_delete=models.CASCADE)
    at_home = models.BooleanField()
    score = models.PositiveSmallIntegerField(default=0)

    @classmethod
    def get_or_create_from_raw_data(
        cls: Type[T], match: Match, match_data: Union[CleanFixtureData, MatchData]
    ) -> Tuple[T, T]:
        """
        Get or create a pair of team-match record from an associated match
        and row of fixture data
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
        team, _was_created = Team.objects.get_or_create(name=team_name)

        team_score = match_data.get(f"{team_prefix}_score", 0)
        team_match = TeamMatch(
            team=team, match=match, at_home=at_home, score=team_score
        )

        team_match.full_clean()
        team_match.save()

        return team_match
