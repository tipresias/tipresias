"""Module for scraping data from afl.com.au"""

from typing import Optional, Dict, List, Tuple
import itertools
import re
from datetime import date, datetime
import warnings
from urllib.parse import urljoin
from bs4 import BeautifulSoup, element
import requests
import pandas as pd

from machine_learning.data_config import TEAM_TRANSLATIONS

AFL_DOMAIN = "https://www.afl.com.au"
# afl.com.au always lists the home team first, which is standard convention across
# data sources
HOME_TEAM_IDX = 0
AWAY_TEAM_IDX = 1


def _translate_team_name(team_name: str):
    if team_name in TEAM_TRANSLATIONS.keys():
        return TEAM_TRANSLATIONS[team_name]

    return team_name


def _parse_team_data(team_element: element) -> Tuple[str, List[Dict[str, str]]]:
    team_player_labels = itertools.islice(team_element.stripped_strings, None, None, 2)

    team_name = next(team_player_labels)

    return (
        team_name,
        [
            {"playing_for": team_name, "player_name": player_name}
            for player_name in team_player_labels
        ],
    )


def _parse_game_datetime(game_element: element) -> datetime:
    game_time = list(game_element.stripped_strings)[-1]
    game_time_with_blanks_removed = re.sub(r"^[^\d]+", "", game_time)
    game_datetime_string = re.sub(r"(pm|am)[^,]+", "\\1", game_time_with_blanks_removed)

    return datetime.strptime(game_datetime_string, "%I:%M%p, %B %d, %Y")


def _parse_game_data(
    game_index: int, game_element: element, roster_element: element
) -> List[Dict[str, str]]:
    game_datetime = _parse_game_datetime(game_element)
    team_elements = roster_element.select("ul")

    team_player_data = [
        _parse_team_data(team_element) for team_element in team_elements
    ]
    team_names, player_lists = zip(*team_player_data)

    game_data = {
        "date": game_datetime,
        "match_id": str(game_index),
        "home_team": team_names[HOME_TEAM_IDX],
        "away_team": team_names[AWAY_TEAM_IDX],
    }

    return [
        {**game_data, **player_data}
        for player_data in itertools.chain.from_iterable(player_lists)
    ]


def _fetch_rosters(round_number: int) -> List[Dict[str, str]]:
    round_param = {} if round_number is None else {"round": round_number}
    response = requests.get(urljoin(AFL_DOMAIN, "news/teams"), params=round_param)
    soup = BeautifulSoup(response.text, "html5lib")
    game_elements = soup.select("#tteamlist .lineup-detail .game-time")
    roster_elements = soup.select("#tteamlist .list-inouts")

    if not any(game_elements) or not any(roster_elements):
        warnings.warn(
            "Could not find any game  or roster data. This is likely due to round "
            f"number {round_number} not having any data yet. Returning an empty list."
        )
        return []

    round_data = [
        _parse_game_data(game_index, game_element, roster_element)
        for game_index, (game_element, roster_element) in enumerate(
            zip(game_elements, roster_elements)
        )
    ]

    return list(itertools.chain.from_iterable(round_data))


def get_rosters(
    round_number: int, year: Optional[int] = date.today().year
) -> pd.DataFrame:
    """Fetches roster data for the upcoming round from afl.com.au"""

    roster_data = _fetch_rosters(round_number)

    if not any(roster_data):
        return pd.DataFrame(
            columns=[
                "date",
                "round_number",
                "year",
                "match_id",
                "playing_for",
                "player_name",
                "home_team",
                "away_team",
            ]
        )

    roster_data_frame = pd.DataFrame(roster_data)

    return roster_data_frame.assign(
        round_number=round_number,
        year=year,
        match_id=lambda df: str(year) + "." + str(round_number) + "." + df["match_id"],
        playing_for=lambda df: df["playing_for"].map(_translate_team_name),
        home_team=lambda df: df["home_team"].map(_translate_team_name),
        away_team=lambda df: df["away_team"].map(_translate_team_name),
    )
