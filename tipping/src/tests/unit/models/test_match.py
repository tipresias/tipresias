# pylint: disable=missing-docstring,redefined-outer-name

from unittest.mock import patch
from datetime import date

import pytest
from faker import Faker
import numpy as np

from tests.fixtures.factories import TeamFactory, MatchFactory
from tests.fixtures.data_factories import fake_fixture_data
from tests.helpers.model_helpers import assert_deep_equal_attributes
from tipping.models.base_model import ValidationError
from tipping.models.match import Match, _MatchRecordCollection


FAKE = Faker()
BIG_NUMBER = 999


@pytest.fixture()
def match_collection():
    matches = [MatchFactory.build(add_id=True) for _ in range(10)]
    return _MatchRecordCollection(records=matches)


@pytest.mark.parametrize(
    ["invalid_attribute", "error_message"],
    [
        ({"start_date_time": FAKE.date_time()}, "must be set to the UTC timezone"),
        ({"season": np.random.randint(-BIG_NUMBER, 1)}, "min value is 1"),
        ({"round_number": np.random.randint(-BIG_NUMBER, 1)}, "min value is 1"),
        ({"venue": ""}, "empty values not allowed"),
        ({"winner": "Team Name"}, "must be of team type"),
        ({"winner": TeamFactory.build()}, "must have an ID"),
        ({"margin": np.random.randint(-BIG_NUMBER, 0)}, "min value is 0"),
    ],
)
@patch("tipping.models.base_model.FaunadbClient.graphql")
def test_saving_invalid_match(mock_graphql, invalid_attribute, error_message):
    valid_attributes = {
        key: value
        for key, value in MatchFactory.build().attributes.items()
        if key not in ["id", "team_matches"]
    }
    match = Match(**{**valid_attributes, **{"team_matches": []}, **invalid_attribute})

    # It raises a ValidateionError
    with pytest.raises(ValidationError, match=error_message):
        match.create()

    # It doesn't save the match
    mock_graphql.assert_not_called()


@pytest.mark.parametrize(
    ["season", "season_variable"], [(None, date.today().year), (1999, 1999)]
)
@patch("tipping.models.base_model.FaunadbClient.graphql")
def test_filtering_matches(mock_graphql, season, season_variable):
    matches = Match.filter_by_season(season=season)

    # It returns a match collection
    assert isinstance(matches, _MatchRecordCollection)

    # It uses season in the query, defaulting to current year
    assert mock_graphql.call_args.args[1]["season"] == season_variable


def test_collection_count(match_collection):
    assert len(match_collection) == match_collection.count()


@pytest.mark.parametrize(
    "match_attributes", [("season",), ("round_number",), ("season", "round_number")]
)
def test_collection_filter(match_collection, match_attributes):
    match = np.random.choice(match_collection)
    filter_values = {attr: getattr(match, attr) for attr in match_attributes}

    filtered_matches = match_collection.filter(**filter_values)

    # It returns a collection
    assert isinstance(filtered_matches, _MatchRecordCollection)

    # It contains at least one match
    assert filtered_matches.count() > 0

    # Record attributes match all filtered values
    for filtered_match in filtered_matches:
        for match_attribute in match_attributes:
            assert getattr(match, match_attribute) == getattr(
                filtered_match, match_attribute
            )


def test_from_db_response():
    winner = TeamFactory.build(add_id=True)
    match = MatchFactory.build(winner=winner, add_id=True)
    db_record = {
        "startDateTime": match.start_date_time.isoformat(),
        "season": match.season,
        "roundNumber": match.round_number,
        "venue": match.venue,
        "margin": match.margin,
        "winner": {"name": match.winner.name, "_id": match.winner.id},
        "teamMatches": {
            "data": [
                {
                    "atHome": tm.at_home,
                    "score": tm.score,
                    "team": {"name": tm.team.name, "_id": tm.team.id},
                    "_id": tm.id,
                }
                for tm in match.team_matches
            ]
        },
        "_id": match.id,
    }

    match_from_record = Match.from_db_response(db_record)

    # It returns a match object
    assert isinstance(match_from_record, Match)

    # It has matching attributes
    assert_deep_equal_attributes(match, match_from_record)


@patch("tipping.models.base_model.FaunadbClient.graphql")
def test_getting_or_creating_match_from_raw_data_with_errors(mock_graphql):
    fixture_data = fake_fixture_data().iloc[0, :]
    mock_responses = {
        "filterMatchesBySeason": {
            "data": [
                {
                    "_id": "1234",
                    "startDateTime": str(fixture_data["date"]),
                    "season": fixture_data["year"],
                    "roundNumber": fixture_data["round_number"],
                    "venue": fixture_data["venue"],
                    "winner": None,
                    "margin": None,
                }
                for _ in range(2)
            ]
        }
    }

    mock_graphql.return_value = mock_responses
    error_message = "either one match record or none"

    # It raises an AssertionError
    with pytest.raises(AssertionError, match=error_message):
        Match.get_or_create_from_raw_data(fixture_data)
