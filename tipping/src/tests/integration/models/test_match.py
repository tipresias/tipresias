# pylint: disable=missing-docstring,redefined-outer-name

from datetime import timedelta, timezone, datetime

import numpy as np
from faker import Faker
from sqlalchemy import select, func, sql
from freezegun import freeze_time
import pytest

from tests.fixtures import data_factories, model_factories
from tipping.models import Match


Fake = Faker()


def test_match_creation(fauna_session):
    match = Match(
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
    upcoming_round_number = int(next_match["round_number"]) + 2

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

    model_factories.FullMatchFactory(
        start_date_time=right_now - timedelta(days=3),
        round_number=1,
    )

    resultless_matches = []
    for n in range(2):
        resultless_matches.append(
            model_factories.FullMatchFactory(
                start_date_time=right_now - timedelta(days=(n + 2)),
                round_number=(n + 2),
                home_team_match__score=None,
                away_team_match__score=None,
            )
        )

    model_factories.FullMatchFactory(
        start_date_time=right_now,
        round_number=4,
        home_team_match__score=None,
        away_team_match__score=None,
    )

    match_query = Match.played_without_results()
    queried_matches = fauna_session.execute(match_query).scalars().all()

    assert len(queried_matches) == 2
    for queried_match in queried_matches:
        assert queried_match in resultless_matches


def test_earliest_without_results(fauna_session):
    right_now = datetime.now(tz=timezone.utc)

    model_factories.FullMatchFactory(
        start_date_time=right_now - timedelta(days=1),
        round_number=2,
        home_team_match__score=None,
        away_team_match__score=None,
    )

    earliest_date = right_now - timedelta(days=2)
    earliest_without_results = model_factories.FullMatchFactory(
        start_date_time=earliest_date,
        round_number=1,
        home_team_match__score=None,
        away_team_match__score=None,
    )

    query = Match.earliest_without_results()
    queried_matches = fauna_session.execute(query).scalars().all()
    assert len(queried_matches) == 1
    assert queried_matches[0] == earliest_without_results


def test_update_results(fauna_session):
    match_results = data_factories.fake_match_results_data()
    match_results_to_update = match_results.iloc[:3, :]
    matches = []

    for _idx, match_result in match_results_to_update.iterrows():
        match = model_factories.FullMatchFactory(
            start_date_time=match_result["date"],
            round_number=match_result["round_number"],
            home_team_match__team__name=match_result["home_team"],
            away_team_match__team__name=match_result["away_team"],
        )

        matches.append(match)

    Match.update_results(matches, match_results)

    queried_matches = fauna_session.execute(sql.select(Match)).scalars().all()
    for match in queried_matches:
        assert match.margin is not None
        assert match.winner_id is not None

        for team_match in match.team_matches:
            assert team_match.score is not None

        for prediction in match.predictions:
            assert prediction.is_correct is not None


def test_get_or_build(fauna_session):
    # Need to turn off autoflush to keep SQLA from saving records before we're ready
    fauna_session.autoflush = False

    match_data = data_factories.fake_fixture_data().iloc[0, :]
    built_match = Match.get_or_build(
        fauna_session,
        venue=match_data["venue"],
        start_date_time=match_data["date"],
        round_number=match_data["round_number"],
    )

    assert match_data["venue"] == built_match.venue
    assert match_data["date"] == built_match.start_date_time
    assert match_data["round_number"] == built_match.round_number

    match_count = fauna_session.execute(select(func.count(Match.id))).scalar()
    assert match_count == 0

    fauna_session.add(built_match)
    fauna_session.commit()

    gotten_match = Match.get_or_build(
        fauna_session,
        venue=built_match.venue,
        start_date_time=built_match.start_date_time,
        round_number=built_match.round_number,
    )

    assert gotten_match == built_match


def test_get_by(fauna_session):
    matches = model_factories.MatchFactory.create_batch(5, venue=Fake.company())
    match = matches[np.random.randint(1, len(matches) - 1)]

    blank_match = Match.get_by(
        fauna_session,
        venue=Fake.company(),
        start_date_time=Fake.date_time_this_month(tzinfo=timezone.utc),
        round_number=Fake.pyint(),
    )

    assert blank_match is None

    gotten_match = Match.get_by(
        fauna_session,
        venue=match.venue,
        start_date_time=match.start_date_time,
        round_number=match.round_number,
    )

    assert gotten_match == match

    gotten_match = Match.get_by(fauna_session, venue=match.venue)

    assert gotten_match == matches[0]
