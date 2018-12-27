from datetime import datetime, timezone
from typing import List, Optional
from django.core.management.base import BaseCommand
import pandas as pd
import numpy as np
from mypy_extensions import TypedDict

from server.data_processors import FitzroyDataReader
from server.models import Match, TeamMatch, Team
from server.ml_models import BettingModel, MatchModel, PlayerModel, AllModel, AvgModel
from server.ml_models.betting_model import BettingModelData
from server.ml_models.match_model import MatchModelData
from server.ml_models.player_model import PlayerModelData
from server.ml_models.all_model import AllModelData

FixtureData = TypedDict(
    "FixtureData",
    {
        "date": pd.Timestamp,
        "season": int,
        "season_game": int,
        "round": int,
        "home_team": str,
        "away_team": str,
        "venue": str,
    },
)

NO_SCORE = 0
ML_MODELS = [
    (BettingModel(name="betting_data"), BettingModelData),
    (MatchModel(name="match_data"), MatchModelData),
    (PlayerModel(name="player_data"), PlayerModelData),
    (AllModel(name="all_data"), AllModelData),
    (AvgModel(name="avg_predictions"), AllModelData),
]


class Command(BaseCommand):
    help = """
    Check if there are upcoming AFL matches and make predictions on results
    for all unplayed matches in the upcoming/current round.
    """

    def __init__(self, *args, data_reader=FitzroyDataReader(), **kwargs) -> None:
        super().__init__(*args, **kwargs)

        self.data_reader = data_reader
        # Fitzroy fixture data uses UTC
        self.right_now = datetime.now(timezone.utc)
        self.current_year = self.right_now.year

    def handle(self, *_args, **_kwargs) -> None:  # pylint disable=W0613
        fixture_data_frame = self.__fetch_fixture_data(self.current_year)

        if fixture_data_frame is None:
            print("Could not fetch data.")
            return None

        fixture_rounds = fixture_data_frame["round"]
        last_round_played = fixture_rounds[
            fixture_data_frame["date"] < self.right_now
        ].max()
        next_round_to_play = fixture_rounds[
            fixture_data_frame["date"] > self.right_now
        ].min()
        saved_match_count = len(
            Match.objects.filter(start_date_time__gt=self.right_now)
        )

        if last_round_played != next_round_to_play and saved_match_count == 0:
            print(
                f"Saving Match and TeamMatch records for round {next_round_to_play}\n"
            )

            next_round_fixture = fixture_data_frame[
                (fixture_data_frame["round"] == next_round_to_play)
            ]
            self.__build_matches(next_round_fixture.to_dict("records"))

        print("Match data already exists in the DB. No new records were created.")
        return None

    def __fetch_fixture_data(self, year: int, retry=True) -> Optional[pd.DataFrame]:
        print(f"Fetching fixture for {self.current_year}...\n")

        try:
            fixture_data_frame = self.data_reader.get_fixture(season=year)
        # fitzRoy raises RuntimeErrors when you try to fetch too far into the future
        except RuntimeError:
            print(
                f"No data found for {year}. It is likely that the fixture "
                "is not yet available. Please try again later.\n"
            )
            return None

        if not any(fixture_data_frame):
            print(f"No data found for {year}.")
            return None

        latest_match = fixture_data_frame["date"].max()

        if self.right_now > latest_match and retry:
            if retry:
                print(
                    f"No unplayed matches found in {year}. We will try to fetch "
                    f"fixture for {year + 1}.\n"
                )

                return self.__fetch_fixture_data((year + 1), retry=False)

            print(
                f"No unplayed matches found in {year}, and we're not going "
                "to keep trying. Please try a season that hasn't been completed.\n"
            )
            return None

        return fixture_data_frame

    def __build_matches(
        self, fixture_data: List[FixtureData]
    ) -> Optional[List[TeamMatch]]:
        if not any(fixture_data):
            print("No match data found for the given season and round number.")
            return None

        team_matches = list(
            np.array(
                [self.__build_match(match_data) for match_data in fixture_data]
            ).flatten()
        )

        if not any(team_matches):
            print("Something went wrong, and no team matches were saved.")
            return None

        TeamMatch.objects.bulk_create(team_matches)

        print("Match data saved!\n")
        return None

    def __build_match(self, match_data: FixtureData) -> List[TeamMatch]:
        match: Match = Match(
            start_date_time=match_data["date"].to_pydatetime(),
            round_number=int(match_data["round"]),
        )
        match.clean()
        match.save()

        return self.__build_team_match(match, match_data)

    @staticmethod
    def __build_team_match(match: Match, match_data: FixtureData) -> List[TeamMatch]:
        home_team = Team.objects.get(name=match_data["home_team"])
        away_team = Team.objects.get(name=match_data["away_team"])

        home_team_match = TeamMatch(
            team=home_team, match=match, at_home=True, score=NO_SCORE
        )
        away_team_match = TeamMatch(
            team=away_team, match=match, at_home=False, score=NO_SCORE
        )

        home_team_match.clean()
        away_team_match.clean()

        return [home_team_match, away_team_match]
