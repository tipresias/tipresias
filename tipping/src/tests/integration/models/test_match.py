# pylint: disable=missing-docstring,redefined-outer-name

from datetime import timedelta, timezone, datetime

import numpy as np
from faker import Faker
from sqlalchemy import select, func
from freezegun import freeze_time
import pytest

from tests.fixtures import data_factories
from tipping.models.match import Match, TeamMatch, Team


FAKE = Faker()


def test_match_creation(fauna_session):
    match = Match(
        start_date_time=FAKE.date_time(tzinfo=timezone.utc),
        round_number=np.random.randint(1, 100),
        venue=FAKE.company(),
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
        assert fauna_session.execute(select(func.count(Match.id))).scalar() == 0

        matches = Match.from_future_fixtures(
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
        matches = Match.from_future_fixtures(
            fauna_session, upcoming_fixture_matches, upcoming_round_number
        )

        assert len(matches) == 0
        total_match_count = fauna_session.execute(select(func.count(Match.id))).scalar()
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
        Match(
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
            Match.from_future_fixtures(
                fauna_session, fixture_matches, upcoming_round_number
            )


def test_played_without_results(fauna_session):
    right_now = datetime.now(tz=timezone.utc)
    two_teams = fauna_session.execute(select(Team).limit(2)).scalars().all()

    played_with_results = Match(
        start_date_time=right_now - timedelta(days=3),
        venue=FAKE.company(),
        round_number=1,
    )
    for team in two_teams:
        played_with_results.team_matches.append(
            TeamMatch(team=team, score=np.random.randint(1, 150))
        )

    resultless_matches = []
    for n in range(2):
        played_without_results = Match(
            start_date_time=right_now - timedelta(days=(n + 2)),
            venue=FAKE.company(),
            round_number=(n + 2),
        )
        for team in two_teams:
            played_without_results.team_matches.append(TeamMatch(team=team, score=None))
        resultless_matches.append(played_without_results)

    unplayed = Match(start_date_time=right_now, venue=FAKE.company(), round_number=4)
    for team in two_teams:
        unplayed.team_matches.append(TeamMatch(team=team, score=None))

    fauna_session.add(played_with_results)
    for resultless_match in resultless_matches:
        fauna_session.add(resultless_match)
    fauna_session.add(unplayed)
    fauna_session.commit()

    match_query = Match.played_without_results()
    queried_matches = fauna_session.execute(match_query).scalars().all()

    assert len(queried_matches) == 2
    for queried_match in queried_matches:
        assert queried_match in resultless_matches


def test_earliest_without_results(fauna_session):
    right_now = datetime.now(tz=timezone.utc)
    two_teams = fauna_session.execute(select(Team).limit(2)).scalars().all()

    played_without_results = Match(
        start_date_time=right_now - timedelta(days=1),
        venue=FAKE.company(),
        round_number=2,
    )
    for team in two_teams:
        played_without_results.team_matches.append(TeamMatch(team=team, score=None))

    earliest_date = right_now - timedelta(days=2)
    earliest_without_results = Match(
        start_date_time=earliest_date,
        venue=FAKE.company(),
        round_number=1,
    )
    for team in two_teams:
        earliest_without_results.team_matches.append(TeamMatch(team=team, score=None))

    fauna_session.add(played_without_results)
    fauna_session.add(earliest_without_results)
    fauna_session.commit()

    query = Match.earliest_without_results()
    queried_matches = fauna_session.execute(query).scalars().all()
    assert len(queried_matches) == 1
    assert queried_matches[0] == earliest_without_results
