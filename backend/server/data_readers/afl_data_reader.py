"""Module for scraping data from afl.com.au"""

from typing import Optional, Dict, List
import itertools
from urllib.parse import urljoin
from bs4 import BeautifulSoup, element
import requests
import pandas as pd


AFL_DOMAIN = "https://www.afl.com.au"
TEAM_SELECTORS = {
    "team-coll": "Collingwood",
    "team-carl": "Carlton",
    "team-stk": "St Kilda",
    "team-port": "Port Adelaide",
    "team-bl": "Brisbane",
    "team-melb": "Melbourne",
    "team-nmfc": "North Melbourne",
    "team-gcfc": "Gold Coast",
    "team-fre": "Fremantle",
    "team-syd": "Sydney",
    "team-gws": "GWS",
    "-mhsoa-orsz": "Adelaide",
    "team-rich": "Richmond",
    "team-haw": "Hawthorn",
    "team-wce": "West Coast",
    "team-geel": "Geelong",
    "team-wb": "Western Bulldogs",
    "team-ess": "Essendon",
}


def _parse_player_data(team_name: str, player_element: element) -> Dict[str, str]:
    return {"team": team_name, "player_name": list(player_element.stripped_strings)[-1]}


def _parse_team_data(
    game_element: element, team_element: element
) -> List[Dict[str, str]]:
    team_name = next(team_element.stripped_strings)
    team_number = "1" if "team1" in team_element["class"] else "2"

    player_selector = f"#fieldInouts .posGroup .team{team_number} .player"

    return [
        _parse_player_data(team_name, player_element)
        for player_element in game_element.select(player_selector)
    ]


def _parse_game_data(game_element: element) -> List[Dict[str, str]]:
    game_data = [
        _parse_team_data(game_element, team_element)
        for team_element in game_element.select(".lineup-detail .team-logo")
    ]

    return list(itertools.chain.from_iterable(game_data))


def _fetch_rosters(round_number: Optional[int]) -> List[Dict[str, str]]:
    round_param = {} if round_number is None else {"round": round_number}
    response = requests.get(urljoin(AFL_DOMAIN, "news/teams"), params=round_param)
    soup = BeautifulSoup(response.text, "html5lib")

    round_data = [
        _parse_game_data(game_element) for game_element in soup.select(".game")
    ]

    return list(itertools.chain.from_iterable(round_data))


def get_rosters(round_number: Optional[int] = None) -> pd.DataFrame:
    """Fetches roster data for the upcoming round from afl.com.au"""

    roster_data = _fetch_rosters(round_number)
    roster_data_frame = pd.DataFrame(roster_data)
    roster_data_frame.loc[:, "round_number"] = round_number

    return roster_data_frame
