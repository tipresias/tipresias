"""Module for functions that add features to data frames via FeatureBuilder.

All functions have the following signature:

Args:
    data_frame (pandas.DataFrame): Data frame to be transformed.

Returns:
    pandas.DataFrame
"""

import pandas as pd
import numpy as np

TEAM_LEVEL = 0
YEAR_LEVEL = 1
WIN_POINTS = 4
AVG_SEASON_LENGTH = 23
INDEX_COLS = ['year', 'round_number', 'team']


def add_last_week_result(data_frame):
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


def add_last_week_score(data_frame):
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


def add_cum_percent(data_frame):
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


def add_cum_win_points(data_frame):
    """Add a team's cumulative win points (based on cumulative result)"""

    if 'last_week_result' not in data_frame.columns:
        raise ValueError("To calculate cumulative win points, 'last_week_result' "
                         'must be in the data frame, but the columns given were '
                         f'{data_frame.columns}')

    cum_win_points_col = ((data_frame['last_week_result'] * WIN_POINTS)
                          .groupby(level=[TEAM_LEVEL, YEAR_LEVEL])
                          .cumsum())

    return data_frame.assign(cum_win_points=cum_win_points_col)


def add_rolling_pred_win_rate(data_frame):
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


def add_rolling_last_week_win_rate(data_frame):
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


def add_ladder_position(data_frame):
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
def add_win_streak(data_frame):
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
        streaks = []

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
