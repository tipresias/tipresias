"""Module for functions that add features to data frames via FeatureBuilder.

All functions have the following signature:

Args:
    data_frame (pandas.DataFrame): Data frame to be transformed.

Returns:
    pandas.DataFrame
"""

from typing import List, Tuple
import math
import pandas as pd
import numpy as np

TEAM_LEVEL = 0
YEAR_LEVEL = 1
WIN_POINTS = 4
AVG_SEASON_LENGTH = 23
INDEX_COLS = ['team', 'year', 'round_number']
EARTH_RADIUS = 6371

CITIES = {
    'Adelaide': {
        'state': 'SA',
        'lat': -34.9285,
        'long': 138.6007
    },
    'Sydney': {
        'state': 'NSW',
        'lat': -33.8688,
        'long': 151.2093
    },
    'Melbourne': {
        'state': 'VIC',
        'lat': -37.8136,
        'long': 144.9631
    },
    'Geelong': {
        'state': 'VIC',
        'lat': 38.1499,
        'long': 144.3617
    },
    'Perth': {
        'state': 'WA',
        'lat': -31.9505,
        'long': 115.8605
    },
    'Gold Coast': {
        'state': 'QLD',
        'lat': -28.0167,
        'long': 153.4000
    },
    'Brisbane': {
        'state': 'QLD',
        'lat': -27.4698,
        'long': 153.0251
    },
    'Launceston': {
        'state': 'TAS',
        'lat': -41.4332,
        'long': 147.1441
    },
    'Canberra': {
        'state': 'ACT',
        'lat': -35.2809,
        'long': 149.1300
    },
    'Hobart': {
        'state': 'TAS',
        'lat': -42.8821,
        'long': 147.3272
    },
    'Darwin': {
        'state': 'NT',
        'lat': -12.4634,
        'long': 130.8456
    },
    'Alice Springs': {
        'state': 'NT',
        'lat': -23.6980,
        'long': 133.8807
    },
    'Wellington': {
        'state': 'NZ',
        'lat': -41.2865,
        'long': 174.7762
    },
    'Euroa': {
        'state': 'VIC',
        'lat': -36.7500,
        'long': 145.5667
    },
    'Yallourn': {
        'state': 'VIC',
        'lat': -38.1803,
        'long': 146.3183
    },
    'Cairns': {
        'state': 'QLD',
        'lat': -6.9186,
        'long': 145.7781
    },
    'Ballarat': {
        'state': 'VIC',
        'lat': -37.5622,
        'long': 143.8503
    },
    'Shanghai': {
        'state': 'CHN',
        'lat': 31.2304,
        'long': 121.4737
    },
    'Albury': {
        'state': 'NSW',
        'lat': 36.0737,
        'long': 146.9135
    }
}

TEAM_CITIES = {
    'Adelaide': 'Adelaide',
    'Brisbane Lions': 'Brisbane',
    'Carlton': 'Melbourne',
    'Collingwood': 'Melbourne',
    'Essendon': 'Melbourne',
    'Fitzroy': 'Melbourne',
    'Footscray': 'Melbourne',
    'Fremantle': 'Perth',
    'GWS': 'Sydney',
    'Geelong': 'Geelong',
    'Gold Coast': 'Gold Coast',
    'Hawthorn': 'Melbourne',
    'Melbourne': 'Melbourne',
    'North Melbourne': 'Melbourne',
    'Port Adelaide': 'Adelaide',
    'Richmond': 'Melbourne',
    'St Kilda': 'Melbourne',
    'Sydney': 'Sydney',
    'University': 'Melbourne',
    'West Coast': 'Perth'
}

VENUE_CITIES = {
    'Football Park': 'Adelaide',
    'S.C.G.': 'Sydney',
    'Windy Hill': 'Melbourne',
    'Subiaco': 'Perth',
    'Moorabbin Oval': 'Melbourne',
    'M.C.G.': 'Melbourne',
    'Kardinia Park': 'Geelong',
    'Victoria Park': 'Melbourne',
    'Waverley Park': 'Melbourne',
    'Princes Park': 'Melbourne',
    'Western Oval': 'Melbourne',
    'W.A.C.A.': 'Perth',
    'Carrara': 'Gold Coast',
    'Gabba': 'Brisbane',
    'Docklands': 'Melbourne',
    'York Park': 'Launceston',
    'Manuka Oval': 'Canberra',
    'Sydney Showground': 'Sydney',
    'Adelaide Oval': 'Adelaide',
    'Bellerive Oval': 'Hobart',
    'Marrara Oval': 'Darwin',
    'Traeger Park': 'Alice Springs',
    'Perth Stadium': 'Perth',
    'Stadium Australia': 'Sydney',
    'Wellington': 'Wellington',
    'Lake Oval': 'Melbourne',
    'East Melbourne': 'Melbourne',
    'Corio Oval': 'Geelong',
    'Junction Oval': 'Melbourne',
    'Brunswick St': 'Melbourne',
    'Punt Rd': 'Melbourne',
    'Glenferrie Oval': 'Melbourne',
    'Arden St': 'Melbourne',
    'Olympic Park': 'Melbourne',
    'Yarraville Oval': 'Melbourne',
    'Toorak Park': 'Melbourne',
    'Euroa': 'Euroa',
    'Coburg Oval': 'Melbourne',
    'Brisbane Exhibition': 'Brisbane',
    'North Hobart': 'Hobart',
    'Bruce Stadium': 'Canberra',
    'Yallourn': 'Yallourn',
    "Cazaly's Stadium": 'Cairns',
    'Eureka Stadium': 'Ballarat',
    'Blacktown': 'Sydney',
    'Jiangwan Stadium': 'Shanghai',
    'Albury': 'Albury'
}


def add_last_week_result(data_frame: pd.DataFrame) -> pd.DataFrame:
    """Add a team's last week result (win, draw, loss) as float"""

    if 'score' not in data_frame.columns or 'oppo_score' not in data_frame.columns:
        raise ValueError("To calculate last week result, 'score' and 'oppo_score' "
                         "must be in the data frame, but the columns given were "
                         f"{data_frame.columns}")

    wins = (data_frame['score'] > data_frame['oppo_score']).astype(int)
    draws = ((data_frame['score'] == data_frame['oppo_score'])
             .astype(int) * 0.5)
    last_week_result_col = (wins + draws).groupby(level=TEAM_LEVEL).shift()

    return data_frame.assign(last_week_result=last_week_result_col)


def add_last_week_score(data_frame: pd.DataFrame) -> pd.DataFrame:
    """Add a team's score from their previous match"""

    if 'score' not in data_frame.columns or 'oppo_score' not in data_frame.columns:
        raise ValueError("To calculate last week result, 'score' and 'oppo_score' "
                         "must be in the data frame, but the columns given "
                         f"were {data_frame.columns}")

    # Group by team (not team & year) to get final score from previous season for round 1.
    # This reduces number of rows that need to be dropped and prevents a 'cold start'
    # for cumulative features
    last_week_score_col = data_frame.groupby(level=TEAM_LEVEL)['score'].shift()

    return data_frame.assign(last_week_score=last_week_score_col)


def add_cum_percent(data_frame: pd.DataFrame) -> pd.DataFrame:
    """Add a team's cumulative percent (cumulative score / cumulative opponents' score)"""

    if ('last_week_score' not in data_frame.columns or
            'oppo_last_week_score' not in data_frame.columns):
        raise ValueError("To calculate cum percent, 'last_week_score' and "
                         "'oppo_last_week_score' must be in the data frame, "
                         f'but the columns given were {data_frame.columns}')

    cum_last_week_score = (data_frame['last_week_score']
                           .groupby(level=[TEAM_LEVEL, YEAR_LEVEL])
                           .cumsum())
    cum_oppo_last_week_score = (data_frame['last_week_score']
                                .groupby(level=[TEAM_LEVEL, YEAR_LEVEL])
                                .cumsum())

    return data_frame.assign(cum_percent=cum_last_week_score / cum_oppo_last_week_score)


def add_cum_win_points(data_frame: pd.DataFrame) -> pd.DataFrame:
    """Add a team's cumulative win points (based on cumulative result)"""

    if 'last_week_result' not in data_frame.columns:
        raise ValueError("To calculate cumulative win points, 'last_week_result' "
                         'must be in the data frame, but the columns given were '
                         f'{data_frame.columns}')

    cum_win_points_col = ((data_frame['last_week_result'] * WIN_POINTS)
                          .groupby(level=[TEAM_LEVEL, YEAR_LEVEL])
                          .cumsum())

    return data_frame.assign(cum_win_points=cum_win_points_col)


def add_rolling_pred_win_rate(data_frame: pd.DataFrame) -> pd.DataFrame:
    """Add a team's predicted win rate per the betting odds"""

    odds_cols = ['win_odds', 'oppo_win_odds', 'line_odds', 'oppo_line_odds']

    if any((odds_col not in data_frame.columns for odds_col in odds_cols)):
        raise ValueError(f'To calculate rolling predicted win rate, all odds columns ({odds_cols})'
                         'must be in data frame, but the columns given were '
                         f'{data_frame.columns}')

    is_favoured = ((data_frame['win_odds'] < data_frame['oppo_win_odds']) |
                   (data_frame['line_odds'] < data_frame['oppo_line_odds'])).astype(int)
    odds_are_even = ((data_frame['win_odds'] == data_frame['oppo_win_odds']) &
                     (data_frame['line_odds'] == data_frame['oppo_line_odds'])).astype(int)

    # Give half point for predicted draws
    predicted_results = is_favoured + (odds_are_even * 0.5)

    groups = predicted_results.groupby(level=TEAM_LEVEL, group_keys=False)

    # Using mean season length (23) for rolling window due to a combination of
    # testing different window values for a previous model and finding 23 to be
    # a good window for data vis.
    # Not super scientific, but it works well enough.
    rolling_pred_win_rate = groups.rolling(window=AVG_SEASON_LENGTH).mean()

    # Only select rows that are NaNs in rolling series
    blank_rolling_rows = rolling_pred_win_rate.isna()
    expanding_win_rate = groups.expanding(1).mean()[blank_rolling_rows]
    expanding_rolling_pred_win_rate = (
        pd
        .concat([rolling_pred_win_rate, expanding_win_rate], join='inner')
        .dropna()
        .sort_index()
    )

    return data_frame.assign(rolling_pred_win_rate=expanding_rolling_pred_win_rate)


def add_rolling_last_week_win_rate(data_frame: pd.DataFrame) -> pd.DataFrame:
    """Add a team's win rate through their previous match"""

    if 'last_week_result' not in data_frame.columns:
        raise ValueError("To calculate rolling win rate, 'last_week_result' "
                         'must be in data frame, but the columns given were '
                         f'{data_frame.columns}')

    groups = (data_frame['last_week_result']
              .groupby(level=TEAM_LEVEL, group_keys=False))

    # Using mean season length (23) for rolling window due to a combination of
    # testing different window values for a previous model and finding 23 to be
    # a good window for data vis.
    # Not super scientific, but it works well enough.
    rolling_win_rate = groups.rolling(window=AVG_SEASON_LENGTH).mean()

    # Only select rows that are NaNs in rolling series
    blank_rolling_rows = rolling_win_rate.isna()
    expanding_win_rate = groups.expanding(1).mean()[blank_rolling_rows]
    expanding_rolling_win_rate = (
        pd
        .concat([rolling_win_rate, expanding_win_rate], join='inner')
        .dropna()
        .sort_index()
    )

    return data_frame.assign(rolling_last_week_win_rate=expanding_rolling_win_rate)


def add_ladder_position(data_frame: pd.DataFrame) -> pd.DataFrame:
    """Add a team's current ladder position (based on cumulative win points and percent)"""

    required_cols = INDEX_COLS + ['cum_win_points', 'cum_percent']

    if any((req_col not in data_frame.columns for req_col in required_cols)):
        raise ValueError(f'To calculate ladder position, all required columns ({required_cols})'
                         'must be in the data frame, but the columns given were '
                         f'{data_frame.columns}')

    # Pivot to get round-by-round match points and cumulative percent
    ladder_pivot_table = (
        data_frame[['cum_win_points', 'cum_percent']]
        .pivot_table(
            index=['year', 'round_number'],
            values=['cum_win_points', 'cum_percent'],
            columns='team',
            aggfunc={'cum_win_points': np.sum, 'cum_percent': np.mean}
        )
    )

    # To get round-by-round ladder ranks, we sort each round by win points & percent,
    # then save index numbers
    ladder_index = []
    ladder_values = []

    for year_round_idx, round_row in ladder_pivot_table.iterrows():
        sorted_row = (
            round_row
            .unstack(level=TEAM_LEVEL)
            .sort_values(['cum_win_points', 'cum_percent'], ascending=False)
        )

        for ladder_idx, team_name in enumerate(sorted_row.index.get_values()):
            ladder_index.append(tuple([team_name, *year_round_idx]))
            ladder_values.append(ladder_idx + 1)

    ladder_multi_index = (
        pd
        .MultiIndex
        .from_tuples(ladder_index, names=tuple(INDEX_COLS))
    )
    ladder_position_col = pd.Series(
        ladder_values,
        index=ladder_multi_index,
        name='ladder_position'
    )

    return data_frame.assign(ladder_position=ladder_position_col)


# Calculate win/loss streaks. Positive result (win or draw) adds 1 (or 0.5);
# negative result subtracts 1. Changes in direction (i.e. broken streak) result in
# starting at 1 or -1.
def add_win_streak(data_frame: pd.DataFrame) -> pd.DataFrame:
    """Add a team's running win/loss streak through their previous match"""

    if 'last_week_result' not in data_frame.columns:
        raise ValueError("To calculate win streak, 'last_week_result' "
                         'must be in data frame, but the columns given were '
                         f'{data_frame.columns}')

    last_week_win_groups = (
        data_frame['last_week_result']
        .groupby(level=TEAM_LEVEL, group_keys=False)
    )
    streak_groups = []

    for team_group_key, team_group in last_week_win_groups:
        streaks: List = []

        for idx, result in enumerate(team_group):
            # 1 represents win, 0.5 represents draw
            if result > 0:
                if idx == 0 or streaks[idx - 1] <= 0:
                    streaks.append(result)
                else:
                    streaks.append(streaks[idx - 1] + result)
            # 0 represents loss
            elif result == 0:
                if idx == 0 or streaks[idx - 1] >= 0:
                    streaks.append(-1)
                else:
                    streaks.append(streaks[idx - 1] - 1)
            elif result < 0:
                raise ValueError(f'No results should be negative, but {result} '
                                 f'is at index {idx} of group {team_group_key}')
            else:
                # For a team's first match in the data set or any rogue NaNs, we add 0
                streaks.append(0)

        streak_groups.extend(streaks)

    return data_frame.assign(win_streak=pd.Series(streak_groups, index=data_frame.index))


def add_last_week_goals(data_frame: pd.DataFrame) -> pd.DataFrame:
    """Add the number of goals a team scored in their previous match."""

    last_week_goals = data_frame['goals'].groupby(level=0).shift()

    return data_frame.assign(last_week_goals=last_week_goals).drop('goals', axis=1)


def add_last_week_behinds(data_frame: pd.DataFrame) -> pd.DataFrame:
    """Add the number of behinds a team scored in their previous match."""

    last_week_behinds = data_frame['behinds'].groupby(level=0).shift()

    return data_frame.assign(last_week_behinds=last_week_behinds).drop('behinds', axis=1)


def add_out_of_state(data_frame: pd.DataFrame) -> pd.DataFrame:
    """Add whether a team is playing out of their home state."""

    venue_state = data_frame['venue'].map(
        lambda x: CITIES[VENUE_CITIES[x]]['state']
    )
    team_state = data_frame['team'].map(
        lambda x: CITIES[TEAM_CITIES[x]]['state']
    )

    return data_frame.assign(out_of_state=(team_state != venue_state).astype(int))


def add_travel_distance(data_frame: pd.DataFrame) -> pd.DataFrame:
    """Add distance between each team's home city and the venue city for the match"""

    # https://www.movable-type.co.uk/scripts/latlong.html
    def haversine_formula(lat_long1: Tuple[float, float], lat_long2: Tuple[float, float]) -> float:
        """Formula for distance between two pairs of latitudes & longitudes"""

        lat1, long1 = lat_long1
        lat2, long2 = lat_long2
        # Latitude & longitude are in degrees, so have to convert to radians for
        # trigonometric functions
        phi1 = math.radians(lat1)
        phi2 = math.radians(lat2)
        delta_phi = phi2 - phi1
        delta_lambda = math.radians(long2 - long1)
        a = (math.sin(delta_phi / 2)**2 +
             (math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2)**2))
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

        return EARTH_RADIUS * c

    venue_lat_long = data_frame['venue'].map(
        lambda x: (CITIES[VENUE_CITIES[x]]['lat'],
                   CITIES[VENUE_CITIES[x]]['long'])
    )
    team_lat_long = data_frame['team'].map(
        lambda x: (CITIES[TEAM_CITIES[x]]['lat'],
                   CITIES[TEAM_CITIES[x]]['long'])
    )

    return data_frame.assign(travel_distance=[
        haversine_formula(*lats_longs) for lats_longs in zip(venue_lat_long, team_lat_long)
    ])
