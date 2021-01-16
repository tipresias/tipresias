"""Module for app settings, data transformations, and internal conventions."""

import os

SRC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "../")
ENVIRONMENT = os.getenv("PYTHON_ENV", "development")
IS_PRODUCTION = ENVIRONMENT == "production"

API_TOKEN = os.getenv("TIPPING_SERVICE_TOKEN", "")
TIPRESIAS_APP = os.environ["TIPRESIAS_APP"]
TIPRESIAS_APP_TOKEN = os.getenv("TIPRESIAS_APP_TOKEN", "")
DATA_SCIENCE_SERVICE = os.environ["DATA_SCIENCE_SERVICE"]
DATA_SCIENCE_SERVICE_TOKEN = os.getenv("DATA_SCIENCE_SERVICE_TOKEN", "")

FAUNA_SECRET = os.getenv("FAUNA_SECRET", "")
DATABASE_HOST = os.getenv("DATABASE_HOST", "faunadb:8443")
DATABASE_URL = f"fauna://{DATABASE_HOST}/?secret={FAUNA_SECRET}"

TEAM_TRANSLATIONS = {
    "Tigers": "Richmond",
    "Blues": "Carlton",
    "Demons": "Melbourne",
    "Giants": "GWS",
    "GWS Giants": "GWS",
    "Greater Western Sydney": "GWS",
    "Suns": "Gold Coast",
    "Bombers": "Essendon",
    "Swans": "Sydney",
    "Magpies": "Collingwood",
    "Kangaroos": "North Melbourne",
    "Crows": "Adelaide",
    "Bulldogs": "Western Bulldogs",
    "Footscray": "Western Bulldogs",
    "Dockers": "Fremantle",
    "Power": "Port Adelaide",
    "Saints": "St Kilda",
    "Eagles": "West Coast",
    "Lions": "Brisbane",
    "Cats": "Geelong",
    "Hawks": "Hawthorn",
    "Adelaide Crows": "Adelaide",
    "Brisbane Lions": "Brisbane",
    "Brisbane Bears": "Brisbane",
    "Gold Coast Suns": "Gold Coast",
    "Geelong Cats": "Geelong",
    "West Coast Eagles": "West Coast",
    "Sydney Swans": "Sydney",
    # Monash footy tipping team names
    "G_W_Sydney": "GWS",
    "W_Bulldogs": "Western Bulldogs",
    "P_Adelaide": "Port Adelaide",
    "Gold_Coast": "Gold Coast",
    "St_Kilda": "St Kilda",
    "W_Coast": "West Coast",
}

VENUE_CITIES = {
    # AFL Tables venues
    "Football Park": "Adelaide",
    "S.C.G.": "Sydney",
    "Windy Hill": "Melbourne",
    "Subiaco": "Perth",
    "Moorabbin Oval": "Melbourne",
    "M.C.G.": "Melbourne",
    "Kardinia Park": "Geelong",
    "Victoria Park": "Melbourne",
    "Waverley Park": "Melbourne",
    "Princes Park": "Melbourne",
    "Western Oval": "Melbourne",
    "W.A.C.A.": "Perth",
    "Carrara": "Gold Coast",
    "Gabba": "Brisbane",
    "Docklands": "Melbourne",
    "York Park": "Launceston",
    "Manuka Oval": "Canberra",
    "Sydney Showground": "Sydney",
    "Adelaide Oval": "Adelaide",
    "Bellerive Oval": "Hobart",
    "Marrara Oval": "Darwin",
    "Traeger Park": "Alice Springs",
    "Perth Stadium": "Perth",
    "Stadium Australia": "Sydney",
    "Wellington": "Wellington",
    "Lake Oval": "Melbourne",
    "East Melbourne": "Melbourne",
    "Corio Oval": "Geelong",
    "Junction Oval": "Melbourne",
    "Brunswick St": "Melbourne",
    "Punt Rd": "Melbourne",
    "Glenferrie Oval": "Melbourne",
    "Arden St": "Melbourne",
    "Olympic Park": "Melbourne",
    "Yarraville Oval": "Melbourne",
    "Toorak Park": "Melbourne",
    "Euroa": "Euroa",
    "Coburg Oval": "Melbourne",
    "Brisbane Exhibition": "Brisbane",
    "North Hobart": "Hobart",
    "Bruce Stadium": "Canberra",
    "Yallourn": "Yallourn",
    "Cazaly's Stadium": "Cairns",
    "Eureka Stadium": "Ballarat",
    "Blacktown": "Sydney",
    "Jiangwan Stadium": "Shanghai",
    "Albury": "Albury",
    "Riverway Stadium": "Townsville",
    # Footywire venues
    "AAMI Stadium": "Adelaide",
    "ANZ Stadium": "Sydney",
    "UTAS Stadium": "Launceston",
    "Blacktown International": "Sydney",
    "Blundstone Arena": "Hobart",
    "Domain Stadium": "Perth",
    "Etihad Stadium": "Melbourne",
    "GMHBA Stadium": "Geelong",
    "MCG": "Melbourne",
    "Mars Stadium": "Ballarat",
    "Metricon Stadium": "Gold Coast",
    "Optus Stadium": "Perth",
    "SCG": "Sydney",
    "Spotless Stadium": "Sydney",
    "TIO Stadium": "Darwin",
    "Westpac Stadium": "Wellington",
    "Marvel Stadium": "Melbourne",
    "Canberra Oval": "Canberra",
    "TIO Traeger Park": "Alice Springs",
    # Correct spelling is 'Traeger', but footywire.com is spelling it 'Traegar' in its
    # fixtures, so including both in case they eventually fix the misspelling
    "TIO Traegar Park": "Alice Springs",
}

DEFUNCT_TEAM_NAMES = ["Fitzroy", "University"]
TEAM_NAMES = sorted(DEFUNCT_TEAM_NAMES + list(set(TEAM_TRANSLATIONS.values())))
VENUES = list(set(VENUE_CITIES.keys()))
