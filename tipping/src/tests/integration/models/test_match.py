# pylint: disable=missing-docstring

from datetime import date

import numpy as np

from tests.fixtures.factories import MatchFactory, TeamFactory
from tests.fixtures.data_factories import fake_fixture_data
from tipping.models import Match

REASONABLE_NUMBER_OF_RECORDS = 10


def test_creating_valid_match(faunadb_client):
    match = MatchFactory.build()
    saved_match = match.create()

    # It returns the saved match
    assert saved_match == match

    # It saves the match in the DB
    query = "query { findMatchByID(id: %s) { _id } }" % (saved_match.id)
    result = faunadb_client.graphql(query)
    assert result["findMatchByID"]["_id"]


def test_filtering_matches(faunadb_client):  # pylint: disable=unused-argument
    test_seasons = [1942, 1999]
    match_seasons = test_seasons + [date.today().year]
    filter_seasons = test_seasons + [None]

    for n in range(REASONABLE_NUMBER_OF_RECORDS):
        season = (
            match_seasons[n]
            if n < len(match_seasons)
            else int(np.random.choice(match_seasons))
        )
        MatchFactory.create(season=season)

    filter_season = np.random.choice(filter_seasons)
    matches = Match.filter_by_season(season=filter_season)

    # It returns at least one match
    assert len(matches) > 0

    # It only returns matches in the given season
    assert all([match.season == filter_season for match in matches])


def test_getting_or_creating_match_from_raw_data(faunadb_client):
    fixture_data = fake_fixture_data().iloc[0, :]

    created_match = Match.get_or_create_from_raw_data(fixture_data)

    # It saves the match in the DB
    query = "query { findMatchByID(id: %s) { _id } }" % (created_match.id)
    result = faunadb_client.graphql(query)
    assert result["findMatchByID"]["_id"]

    gotten_match = Match.get_or_create_from_raw_data(fixture_data)

    # It gets the same match
    assert created_match.id == gotten_match.id
