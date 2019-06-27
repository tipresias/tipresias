import re
import pandas as pd
import numpy as np

from machine_learning.settings import DATA_DIR


def raw_betting_df(path=f"{DATA_DIR}/afl_betting.csv"):
    raw_df = pd.read_csv(path, index_col=("date", "venue"), parse_dates=["date"])
    home_df = (
        raw_df[raw_df["home"] == 1]
        .drop("home", axis=1)
        .rename(columns=lambda x: f"home_{x}")
    )
    away_df = (
        raw_df[raw_df["home"] == 0]
        .drop("home", axis=1)
        .rename(columns=lambda x: f"away_{x}")
    )

    return (
        home_df.merge(away_df, on=("date", "venue"))
        .reset_index()
        .set_index(["date", "venue", "home_team", "away_team"])
    )


def raw_match_df(path=f"{DATA_DIR}/ft_match_list.csv"):
    return (
        pd.read_csv(path, parse_dates=["date"])
        .rename(columns={"date": "datetime"})
        .assign(date=lambda x: x["datetime"].map(lambda y: y.date()))
        .set_index(["date", "venue", "home_team", "away_team"])
    )


def betting_df():
    return (
        pd.concat([raw_match_df(), raw_betting_df()], axis=1)
        # The 2017 Grand Final is missing from the betting data for some reason,
        # but other than matches before 2010 that's the only row that should get dropped
        .dropna()
        .reset_index()
        .drop("date", axis=1)
    )


def get_round_number(x):
    DIGITS = re.compile(r"round\s+(\d+)$", flags=re.I)
    QUALIFYING = re.compile("qualifying", flags=re.I)
    ELIMINATION = re.compile("elimination", flags=re.I)
    SEMI = re.compile("semi", flags=re.I)
    PRELIMINARY = re.compile("preliminary", flags=re.I)
    GRAND = re.compile("grand", flags=re.I)

    digits = DIGITS.search(x)
    if digits is not None:
        return int(digits.group(1))
    if QUALIFYING.search(x) is not None:
        return 25
    if ELIMINATION.search(x) is not None:
        return 25
    if SEMI.search(x) is not None:
        return 26
    if PRELIMINARY.search(x) is not None:
        return 27
    if GRAND.search(x) is not None:
        return 28

    raise Exception(f"Round label {x} doesn't match any known patterns")


def betting_model_df(test_year="2017"):
    df = betting_df()

    # Filter out 2017 & 2018 seasons, because they will eventually serve as test sets
    return (
        df[df["datetime"] < f"{test_year}-01-01"]
        .assign(
            round_number=df["season_round"].map(get_round_number),
            year=df["datetime"].map(lambda x: x.year),
        )
        .drop(["venue", "datetime", "crowd", "season_round"], axis=1)
    )


def team_df(df, team_type="home"):
    if team_type not in ("home", "away"):
        raise Exception(
            f'team_type must be either "home" or "away", but {team_type} was given.'
        )

    oppo_team_type = "away" if team_type == "home" else "home"
    at_home_col = np.ones(len(df)) if team_type == "home" else np.zeros(len(df))

    return (
        df.rename(
            columns=lambda x: x.replace(f"{team_type}_", "").replace(
                f"{oppo_team_type}_", "oppo_"
            )
        )
        .assign(at_home=at_home_col)
        .set_index(["team", "year", "round_number"], drop=False)
        .rename_axis([None, None, None])
    )


def team_betting_model_df(df):
    return pd.concat(
        [team_df(df, team_type="home"), team_df(df, team_type="away")], join="inner"
    ).sort_index()


# Get cumulative stats by team & year, then group by team and shift one row
# in order to carry over end of last season for a team's first round ranking
def team_year_cum_col(df, stat_label):
    return (
        df.groupby(level=[0, 1])[stat_label]
        .cumsum()
        .groupby(level=[0])
        .shift()
        .rename(f"cum_{stat_label}")
    )


def team_year_percent(df):
    return (
        team_year_cum_col(df, "score") / team_year_cum_col(df, "oppo_score")
    ).rename("cum_percent")


def team_year_win_points(df):
    # Have to shift scores to make them last week's scores,
    # so ladder position is the one leading up to this week's matches
    wins = (df["score"] > df["oppo_score"]).rename("win")
    draws = (df["score"] == df["oppo_score"]).rename("draw")
    win_points = pd.DataFrame({"win_points": (wins * 4) + (draws * 2)})

    return team_year_cum_col(win_points, "win_points")


def team_year_ladder_position(df):
    # Pivot to get round-by-round match points and cumulative percent
    ladder_pivot_table = pd.concat(
        [team_year_percent(df), team_year_win_points(df)], axis=1
    ).pivot_table(
        index=["year", "round_number"],
        values=["cum_win_points", "cum_percent"],
        columns="team",
        aggfunc={"cum_win_points": np.sum, "cum_percent": np.mean},
    )

    # To get round-by-round ladder ranks, we sort each round by win points & percent,
    # then save index numbers
    ladder_index = []
    ladder_values = []

    for idx, row in ladder_pivot_table.iterrows():
        sorted_row = row.unstack(level=0).sort_values(
            ["cum_win_points", "cum_percent"], ascending=False
        )

        for ladder_idx, team_name in enumerate(sorted_row.index.get_values()):
            ladder_index.append(tuple([team_name, *idx]))
            ladder_values.append(ladder_idx + 1)

    ladder_multi_index = pd.MultiIndex.from_tuples(
        ladder_index, names=("team", "year", "round_number")
    )
    return pd.Series(ladder_values, index=ladder_multi_index, name="ladder_position")


def team_year_oppo_feature(column_label):
    rename_columns = {"oppo_team": "team"}
    rename_columns[column_label] = f"oppo_{column_label}"

    return lambda x: (
        x.loc[:, ["year", "round_number", "oppo_team", column_label]]
        # We switch out oppo_team for team in the index, then assign feature
        # as oppo_{feature_column}
        .rename(columns=rename_columns)
        .set_index(["team", "year", "round_number"])
        .sort_index()
    )


# Function to get rolling mean without losing the first n rows of data by filling
# the with an expanding mean
def rolling_team_rate(series):
    groups = series.groupby(level=0, group_keys=False)
    rolling_win_rate = groups.rolling(window=23).mean()
    expanding_win_rate = (
        groups.expanding(1).mean()
        # Only select rows that are NaNs in rolling series
        [rolling_win_rate.isna()]
    )

    return (
        pd.concat([rolling_win_rate, expanding_win_rate], join="inner")
        .dropna()
        .sort_index()
    )


def rolling_pred_win_rate(df):
    wins = df["line_odds"] < 0
    draws = (df["line_odds"] == 0) * 0.5
    return rolling_team_rate(wins + draws)


def last_week_result(df):
    wins = df["last_week_score"] > df["last_week_oppo_score"]
    draws = (df["last_week_score"] == df["last_week_oppo_score"]) * 0.5
    return wins + draws


def rolling_last_week_win_rate(df):
    return rolling_team_rate(last_week_result(df))


# Calculate win/loss streaks. Positive result (win or draw) adds 1 (or 0.5);
# negative result subtracts 1. Changes in direction (i.e. broken streak) result in
# starting at 1 or -1.
def win_streak(df):
    last_week_win_groups = (
        last_week_result(df).dropna().groupby(level=0, group_keys=False)
    )
    streak_groups = []

    for group_key, group in last_week_win_groups:
        streaks = []

        for idx, result in enumerate(group):
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
            else:
                raise Exception(
                    f"No results should be negative, but {result} is at index {idx}"
                    f"of group {group_key}"
                )

        streak_groups.extend(streaks)

    return pd.Series(streak_groups, index=df.index)


def cum_team_df(df):
    return (
        df.assign(
            ladder_position=team_year_ladder_position,
            cum_percent=team_year_percent,
            cum_win_points=team_year_win_points,
            last_week_score=lambda x: x.groupby(level=0)["score"].shift(),
            last_week_oppo_score=lambda x: x.groupby(level=0)["oppo_score"].shift(),
            rolling_pred_win_rate=rolling_pred_win_rate,
        )
        # oppo features depend on associated cumulative feature,
        # so they need to be assigned after
        .assign(
            oppo_ladder_position=team_year_oppo_feature("ladder_position"),
            oppo_cum_percent=team_year_oppo_feature("cum_percent"),
            oppo_cum_win_points=team_year_oppo_feature("cum_win_points"),
            oppo_rolling_pred_win_rate=team_year_oppo_feature("rolling_pred_win_rate"),
        )
        # Columns that depend on last week's results depend on last_week_score
        # and last_week_oppo_score
        .assign(
            rolling_last_week_win_rate=rolling_last_week_win_rate, win_streak=win_streak
        ).assign(
            oppo_rolling_last_week_win_rate=team_year_oppo_feature(
                "rolling_last_week_win_rate"
            ),
            oppo_win_streak=team_year_oppo_feature("win_streak"),
        )
        # Drop first round as it's noisy due to most data being from previous week's match
        .dropna()
        # Gotta drop duplicates, because St Kilda & Carlton tied a Grand Final
        # in 2010 and had to replay it
        .drop_duplicates(subset=["team", "year", "round_number"], keep="last")
    )
