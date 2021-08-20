# pylint: disable=missing-docstring,redefined-outer-name

from datetime import timedelta, timezone, datetime

import numpy as np
from faker import Faker
from sqlalchemy import select, func, sql
from freezegun import freeze_time
import pytest

from tests.fixtures import data_factories
from tipping import models


Fake = Faker()


def test_match_creation(fauna_session):
    match = models.Match(
        start_date_time=Fake.date_time(tzinfo=timezone.utc),
        round_number=np.random.randint(1, 100),
        venue=Fake.company(),
    )
    fauna_session.add(match)
    fauna_session.commit()

    assert match.id is not None


def test_from_future_fixtures(fauna_session):
    fixture_matches = data_factories.fake_fixture_data()
    next_match = fixture_matches.iloc[np.random.randint(0, len(fixture_matches)), :]
    patched_date = next_match["date"].to_pydatetime() - timedelta(days=1)
    upcoming_round_number = next_match["round_number"]
    upcoming_fixture_matches = fixture_matches.query(
        "round_number == @upcoming_round_number"
    )

    with freeze_time(patched_date):
        assert fauna_session.execute(select(func.count(models.Match.id))).scalar() == 0

        matches = models.Match.from_future_fixtures(
            fauna_session, upcoming_fixture_matches, upcoming_round_number
        )
        created_match_count = len(matches)

        assert created_match_count == len(
            upcoming_fixture_matches.query("date > @patched_date")
        )

        for match in matches:
            fauna_session.add(match)

        fauna_session.commit()

        # With existing matches in DB
        matches = models.Match.from_future_fixtures(
            fauna_session, upcoming_fixture_matches, upcoming_round_number
        )

        assert len(matches) == 0
        total_match_count = fauna_session.execute(
            select(func.count(models.Match.id))
        ).scalar()
        assert total_match_count == created_match_count


def _get_matches_from_different_days(fixture_matches):
    first_match = fixture_matches.iloc[0, :]
    next_match_idx = np.random.randint(1, len(fixture_matches))
    next_match = fixture_matches.iloc[next_match_idx, :]

    while True:
        if next_match["date"].to_pydatetime() > first_match[
            "date"
        ].to_pydatetime() + timedelta(days=1):
            break

        next_match_idx = next_match_idx + 1
        assert next_match_idx < len(fixture_matches)

        next_match = fixture_matches.iloc[next_match_idx, :]

    return first_match, next_match


def test_from_future_fixtures_with_skipped_round(fauna_session):
    fixture_matches = data_factories.fake_fixture_data()
    first_match, next_match = _get_matches_from_different_days(fixture_matches)

    patched_date = next_match["date"].to_pydatetime() - timedelta(days=1)
    upcoming_round_number = int(next_match["round_number"]) + 1

    fauna_session.add(
        models.Match(
            start_date_time=first_match["date"].to_pydatetime(),
            round_number=first_match["round_number"],
            venue=first_match["venue"],
        )
    )
    fauna_session.commit()

    with freeze_time(patched_date):
        with pytest.raises(
            AssertionError,
            match="Expected upcoming round number to be 1 greater than previous round",
        ):
            models.Match.from_future_fixtures(
                fauna_session, fixture_matches, upcoming_round_number
            )
            # Logging to catch cause of flaky test
            print(first_match)
            print(next_match)


def test_played_without_results(fauna_session):
    right_now = datetime.now(tz=timezone.utc)
    two_teams = fauna_session.execute(select(models.Team).limit(2)).scalars().all()

    played_with_results = models.Match(
        start_date_time=right_now - timedelta(days=3),
        venue=Fake.company(),
        round_number=1,
    )
    for team in two_teams:
        played_with_results.team_matches.append(
            models.TeamMatch(team=team, score=np.random.randint(1, 150))
        )

    resultless_matches = []
    for n in range(2):
        played_without_results = models.Match(
            start_date_time=right_now - timedelta(days=(n + 2)),
            venue=Fake.company(),
            round_number=(n + 2),
        )
        for team in two_teams:
            played_without_results.team_matches.append(
                models.TeamMatch(team=team, score=None)
            )
        resultless_matches.append(played_without_results)

    unplayed = models.Match(
        start_date_time=right_now, venue=Fake.company(), round_number=4
    )
    for team in two_teams:
        unplayed.team_matches.append(models.TeamMatch(team=team, score=None))

    fauna_session.add(played_with_results)
    for resultless_match in resultless_matches:
        fauna_session.add(resultless_match)
    fauna_session.add(unplayed)
    fauna_session.commit()

    match_query = models.Match.played_without_results()
    queried_matches = fauna_session.execute(match_query).scalars().all()

    assert len(queried_matches) == 2
    for queried_match in queried_matches:
        assert queried_match in resultless_matches


def test_earliest_without_results(fauna_session):
    right_now = datetime.now(tz=timezone.utc)
    two_teams = fauna_session.execute(select(models.Team).limit(2)).scalars().all()

    played_without_results = models.Match(
        start_date_time=right_now - timedelta(days=1),
        venue=Fake.company(),
        round_number=2,
    )
    for team in two_teams:
        played_without_results.team_matches.append(
            models.TeamMatch(team=team, score=None)
        )

    earliest_date = right_now - timedelta(days=2)
    earliest_without_results = models.Match(
        start_date_time=earliest_date,
        venue=Fake.company(),
        round_number=1,
    )
    for team in two_teams:
        earliest_without_results.team_matches.append(
            models.TeamMatch(team=team, score=None)
        )

    fauna_session.add(played_without_results)
    fauna_session.add(earliest_without_results)
    fauna_session.commit()

    query = models.Match.earliest_without_results()
    queried_matches = fauna_session.execute(query).scalars().all()
    assert len(queried_matches) == 1
    assert queried_matches[0] == earliest_without_results


def test_update_results(fauna_session):
    match_results = data_factories.fake_match_results_data()
    match_results_to_update = match_results.iloc[:3, :]
    matches = []

    for _idx, match_result in match_results_to_update.iterrows():
        home_team, away_team = [
            fauna_session.execute(
                sql.select(models.Team).where(models.Team.name == match_result[team])
            )
            .scalars()
            .first()
            for team in ["home_team", "away_team"]
        ]

        match = models.Match(
            start_date_time=match_result["date"],
            venue=Fake.company(),
            round_number=match_result["round_number"],
            team_matches=[
                models.TeamMatch(
                    team=home_team,
                    at_home=True,
                ),
                models.TeamMatch(
                    team=away_team,
                    at_home=False,
                ),
            ],
            predictions=[
                models.Prediction(
                    ml_model=models.MLModel(
                        name=Fake.company(), prediction_type="margin"
                    ),
                    predicted_winner=home_team,
                    predicted_margin=np.random.randint(0, 100),
                )
            ],
        )
        matches.append(match)
        fauna_session.add(match)

    fauna_session.commit()

    models.Match.update_results(matches, match_results)
    fauna_session.commit()

    queried_matches = fauna_session.execute(sql.select(models.Match)).scalars().all()
    for match in queried_matches:
        assert match.margin is not None
        assert match.winner_id is not None

        for team_match in match.team_matches:
            assert team_match.score is not None

        for prediction in match.predictions:
            assert prediction.is_correct is not None
