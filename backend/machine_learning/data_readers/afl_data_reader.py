"""Module for scraping data from afl.com.au"""

from typing import Optional, Dict, List
import itertools
from datetime import date
import warnings
from urllib.parse import urljoin
from bs4 import BeautifulSoup, element
import requests
import pandas as pd

from machine_learning.data_config import TEAM_TRANSLATIONS

AFL_DOMAIN = "https://www.afl.com.au"


def _translate_team_name(team_name: str):
    if team_name in TEAM_TRANSLATIONS.keys():
        return TEAM_TRANSLATIONS[team_name]

    return team_name


def _parse_player_data(player_element: element) -> str:
    return list(player_element.stripped_strings)[-1]


def _parse_team_data(
    game_element: element, team_element: element
) -> List[Dict[str, str]]:
    team_name = next(team_element.stripped_strings)
    team_number = "1" if "team1" in team_element["class"] else "2"

    player_selector = f"#fieldInouts .posGroup .team{team_number} .player"

    return [
        {"playing_for": team_name, "player_name": _parse_player_data(player_element)}
        for player_element in game_element.select(player_selector)
    ]


def _parse_game_data(game_index: int, game_element: element) -> List[Dict[str, str]]:
    team_elements = game_element.select(".lineup-detail .team-logo")
    team_names = [team_element.stripped_strings for team_element in team_elements]
    game_data = {
        "home_team": next(team_names[0]),
        "away_team": next(team_names[1]),
        "match_id": str(game_index),
    }

    player_data_lists = [
        _parse_team_data(game_element, team_element) for team_element in team_elements
    ]

    return [
        {**game_data, **player_data}
        for player_data in itertools.chain.from_iterable(player_data_lists)
    ]


def _fetch_rosters(round_number: Optional[int]) -> List[Dict[str, str]]:
    round_param = {} if round_number is None else {"round": round_number}
    response = requests.get(urljoin(AFL_DOMAIN, "news/teams"), params=round_param)
    soup = BeautifulSoup(response.text, "html5lib")
    game_elements = soup.select(".game")

    if not any(game_elements):
        warnings.warn(
            "Could not find any game data. This is likely due to round number "
            f"{round_number} not having any data yet. Returning an empty list."
        )
        return []

    round_data = [
        _parse_game_data(game_index, game_element)
        for game_index, game_element in enumerate(game_elements)
    ]

    return list(itertools.chain.from_iterable(round_data))


def get_rosters(
    round_number: Optional[int] = None, year: Optional[int] = None
) -> pd.DataFrame:
    """Fetches roster data for the upcoming round from afl.com.au"""

    year = date.today().year if year is None else year
    roster_data = _fetch_rosters(round_number)

    if not any(roster_data):
        return pd.DataFrame(
            columns=[
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
