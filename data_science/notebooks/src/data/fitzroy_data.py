import sys
import math

from machine_learning.settings import BASE_DIR

if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

from machine_learning.data_import import FitzroyDataImporter
from machine_learning.data_processors import TeamDataStacker, FeatureBuilder
from machine_learning.data_processors.feature_functions import (
    add_shifted_team_features,
    add_result,
    add_cum_percent,
    add_cum_win_points,
    add_ladder_position,
    add_win_streak,
)
from machine_learning.data_processors.feature_calculation import (
    feature_calculator,
    calculate_rolling_rate,
)

COL_TRANSLATIONS = {
    "home_points": "home_score",
    "away_points": "away_score",
    "margin": "home_margin",
    "season": "year",
}
INDEX_COLS = ["team", "year", "round_number"]
EARTH_RADIUS = 6371

CITIES = {
    "Adelaide": {"state": "SA", "lat": -34.9285, "long": 138.6007},
    "Sydney": {"state": "NSW", "lat": -33.8688, "long": 151.2093},
    "Melbourne": {"state": "VIC", "lat": -37.8136, "long": 144.9631},
    "Geelong": {"state": "VIC", "lat": 38.1499, "long": 144.3617},
    "Perth": {"state": "WA", "lat": -31.9505, "long": 115.8605},
    "Gold Coast": {"state": "QLD", "lat": -28.0167, "long": 153.4000},
    "Brisbane": {"state": "QLD", "lat": -27.4698, "long": 153.0251},
    "Launceston": {"state": "TAS", "lat": -41.4332, "long": 147.1441},
    "Canberra": {"state": "ACT", "lat": -35.2809, "long": 149.1300},
    "Hobart": {"state": "TAS", "lat": -42.8821, "long": 147.3272},
    "Darwin": {"state": "NT", "lat": -12.4634, "long": 130.8456},
    "Alice Springs": {"state": "NT", "lat": -23.6980, "long": 133.8807},
    "Wellington": {"state": "NZ", "lat": -41.2865, "long": 174.7762},
    "Euroa": {"state": "VIC", "lat": -36.7500, "long": 145.5667},
    "Yallourn": {"state": "VIC", "lat": -38.1803, "long": 146.3183},
    "Cairns": {"state": "QLD", "lat": -6.9186, "long": 145.7781},
    "Ballarat": {"state": "VIC", "lat": -37.5622, "long": 143.8503},
    "Shanghai": {"state": "CHN", "lat": 31.2304, "long": 121.4737},
    "Albury": {"state": "NSW", "lat": 36.0737, "long": 146.9135},
}

TEAM_CITIES = {
    "Adelaide": "Adelaide",
    "Brisbane Lions": "Brisbane",
    "Carlton": "Melbourne",
    "Collingwood": "Melbourne",
    "Essendon": "Melbourne",
    "Fitzroy": "Melbourne",
    "Footscray": "Melbourne",
    "Fremantle": "Perth",
    "GWS": "Sydney",
    "Geelong": "Geelong",
    "Gold Coast": "Gold Coast",
    "Hawthorn": "Melbourne",
    "Melbourne": "Melbourne",
    "North Melbourne": "Melbourne",
    "Port Adelaide": "Adelaide",
    "Richmond": "Melbourne",
    "St Kilda": "Melbourne",
    "Sydney": "Sydney",
    "University": "Melbourne",
    "West Coast": "Perth",
}

VENUE_CITIES = {
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
}


def fitzroy():
    FitzroyDataImporter()


def add_last_week_goals(data_frame):
    last_week_goals = data_frame["goals"].groupby(level=0).shift()

    return data_frame.assign(last_week_goals=last_week_goals).drop(
        ["goals", "oppo_goals"], axis=1
    )


def add_last_week_behinds(data_frame):
    last_week_behinds = data_frame["behinds"].groupby(level=0).shift()

    return data_frame.assign(last_week_behinds=last_week_behinds).drop(
        ["behinds", "oppo_behinds"], axis=1
    )


def add_out_of_state(data_frame):
    venue_state = data_frame["venue"].map(lambda x: CITIES[VENUE_CITIES[x]]["state"])
    team_state = data_frame["team"].map(lambda x: CITIES[TEAM_CITIES[x]]["state"])

    return data_frame.assign(out_of_state=(team_state != venue_state).astype(int))


# https://www.movable-type.co.uk/scripts/latlong.html
def haversine_formula(lat_long1, lat_long2):
    lat1, long1 = lat_long1
    lat2, long2 = lat_long2
    # Latitude & longitude are in degrees, so have to convert to radians for
    # trigonometric functions
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = phi2 - phi1
    delta_lambda = math.radians(long2 - long1)
    a = math.sin(delta_phi / 2) ** 2 + (
        math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return EARTH_RADIUS * c


def add_travel_distance(data_frame):
    venue_lat_long = data_frame["venue"].map(
        lambda x: (CITIES[VENUE_CITIES[x]]["lat"], CITIES[VENUE_CITIES[x]]["long"])
    )
    team_lat_long = data_frame["team"].map(
        lambda x: (CITIES[TEAM_CITIES[x]]["lat"], CITIES[TEAM_CITIES[x]]["long"])
    )

    return data_frame.assign(
        travel_distance=[
            haversine_formula(*lats_longs)
            for lats_longs in zip(venue_lat_long, team_lat_long)
        ]
    )


def fr_match_data():
    data_frame = (
        fitzroy()
        .get_match_results()
        .rename(columns=COL_TRANSLATIONS)
        .drop(["round", "game", "date"], axis=1)
    )

    data_frame = data_frame[
        ((data_frame["year"] != 1897) | (data_frame["round_number"] != 15))
        & (data_frame["year"] <= 2016)
    ]

    stacked_df = TeamDataStacker(index_cols=INDEX_COLS).transform(data_frame)

    FEATURE_FUNCS = [
        add_result,
        add_shifted_team_features(
            shift_columns=["result", "score", "goals", "behinds"]
        ),
        add_out_of_state,
        add_travel_distance,
        add_cum_percent,
        add_cum_win_points,
        add_ladder_position,
        add_win_streak,
        feature_calculator([(calculate_rolling_rate, [("prev_match_result",)])]),
    ]

    return (
        FeatureBuilder(feature_funcs=FEATURE_FUNCS)
        .transform(stacked_df)
        .drop("venue", axis=1)
        .dropna()
    )
