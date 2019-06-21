import pandas as pd
from notebooks.src.data.fitzroy_data import fitzroy
from machine_learning.data_import import FitzroyDataImporter

STATS_COLS = [
    "player_id",
    "kicks",
    "marks",
    "handballs",
    "goals",
    "behinds",
    "hit_outs",
    "tackles",
    "rebounds",
    "inside_50s",
    "clearances",
    "clangers",
    "frees_for",
    "frees_against",
    "contested_possessions",
    "uncontested_possessions",
    "contested_marks",
    "marks_inside_50",
    "one_percenters",
    "bounces",
    "goal_assists",
    "time_on_ground",
]
MATCH_COLS = [
    "year",
    "home_team",
    "home_score",
    "away_team",
    "away_score",
    "round_number",
    "match_id",
]
MATCH_STATS_COLS = ["at_home", "score", "oppo_score"]
PREV_MATCH_STATS_COLS = [
    f"prev_match_{col}" for col in STATS_COLS if col != "player_id"
]


def id_col(df):
    return (
        df["player_id"].astype(str)
        + df["match_id"].astype(str)
        + df["year"].astype(str)
    )


def player_data(
    start_date="1965-01-01",
    end_date="2016-12-31",
    aggregate=True,
    prev_match_stats=True,
):
    # Player data matches have weird round labelling system (lots of strings for finals matches),
    # so using round numbers from match_results
    match_df = FitzroyDataImporter().match_results()
    player_df = (
        fitzroy()
        .get_afltables_stats(start_date=start_date, end_date=end_date)
        # Some player data venues have trailing spaces
        .assign(venue=lambda x: x["venue"].str.strip())
        # Player data match IDs are wrong for recent years.
        # The easiest way to add correct ones is to graft on the IDs
        # from match_results. Also, match_results round_numbers are more useful.
        .merge(
            match_df[["date", "venue", "round_number", "game"]],
            on=["date", "venue"],
            how="left",
        )
        # As of 11-10-2018, match_results is still missing finals data from 2018.
        # Joining on date/venue leaves two duplicates played at M.C.G.
        # on 29-4-1986 & 9-8-1986, but that's an acceptable loss of data
        # and easier than munging team names
        .dropna()
        .rename(
            columns={
                "season": "year",
                "time_on_ground__": "time_on_ground",
                "id": "player_id",
                "game": "match_id",
            }
        )
        .astype({"year": int, "match_id": int})
        .assign(
            player_name=lambda x: x["first_name"] + " " + x["surname"],
            # Need to add year to ID, because there are some
            # player_id/match_id combos, decades apart, that by chance overlap
            id=id_col,
        )
        .drop(
            [
                "first_name",
                "surname",
                "round",
                "local_start_time",
                "attendance",
                "hq1g",
                "hq1b",
                "hq2g",
                "hq2b",
                "hq3g",
                "hq3b",
                "hq4g",
                "hq4b",
                "aq1g",
                "aq1b",
                "aq2g",
                "aq2b",
                "aq3g",
                "aq3b",
                "aq4g",
                "aq4b",
                "jumper_no_",
                "umpire_1",
                "umpire_2",
                "umpire_3",
                "umpire_4",
                "substitute",
                "group_id",
                "date",
                "venue",
            ],
            axis=1,
        )
        # Some early matches (1800s) have fully-duplicated rows
        .drop_duplicates()
        .set_index("id")
        .sort_index()
    )
    # There were some weird round-robin rounds in the early days, and it's easier to
    # drop them rather than figure out how to split up the rounds.
    player_df = player_df[
        ((player_df["year"] != 1897) | (player_df["round_number"] != 15))
        & ((player_df["year"] != 1924) | (player_df["round_number"] != 19))
    ].sort_values(["player_id", "year", "round_number"])

    if prev_match_stats:
        rename_cols = {
            col: f"prev_match_{col}" for col in STATS_COLS if col != "player_id"
        }
        player_groups = (
            player_df[STATS_COLS]
            .groupby("player_id", group_keys=False)
            .shift()
            .assign(player_id=player_df["player_id"])
            .rename(columns=rename_cols)
            .fillna(0)
            .groupby("player_id", group_keys=False)
        )
    else:
        player_groups = player_df[STATS_COLS].groupby("player_id", group_keys=False)

    rolling_stats = player_groups.rolling(window=23).mean()
    expanding_stats = player_groups.expanding(1).mean()
    expanding_rolling_stats = (
        rolling_stats.fillna(expanding_stats).drop("player_id", axis=1).sort_index()
    )

    brownlow_last_year = (
        player_df[["player_id", "year", "brownlow_votes"]]
        .groupby(["player_id", "year"], group_keys=True)
        .sum()
        # Grouping by player to shift by year
        .groupby(level=0)
        .shift()
        .fillna(0)
        .rename(columns={"brownlow_votes": "last_year_brownlow_votes"})
    )
    brownlow_df = (
        player_df[MATCH_COLS + ["player_id", "playing_for", "player_name"]]
        .merge(brownlow_last_year, on=["player_id", "year"], how="left")
        .set_index(player_df.index)
    )

    player_stats = pd.concat(
        [brownlow_df, expanding_rolling_stats], axis=1, sort=True
    ).assign(cum_games_played=player_groups.cumcount())

    home_stats = (
        player_stats[player_stats["playing_for"] == player_stats["home_team"]]
        .drop(["playing_for"], axis=1)
        .rename(columns=lambda x: x.replace("home_", "").replace("away_", "oppo_"))
        .assign(at_home=1)
    )

    away_stats = (
        player_stats[player_stats["playing_for"] == player_stats["away_team"]]
        .drop(["playing_for"], axis=1)
        .rename(columns=lambda x: x.replace("away_", "").replace("home_", "oppo_"))
        .assign(at_home=0)
    )

    if not aggregate:
        # Need to sort df columns, because pandas freaks out if columns are in different order
        return pd.concat(
            [
                home_stats[home_stats.columns.sort_values()],
                away_stats[away_stats.columns.sort_values()],
            ],
            sort=True,
        ).drop(["player_name", "match_id"], axis=1)

    player_aggs = {
        col: "sum" for col in PREV_MATCH_STATS_COLS + ["last_year_brownlow_votes"]
    }
    # Since match stats are the same across player rows, taking the mean
    # is the easiest way to aggregate them
    match_aggs = {col: "mean" for col in MATCH_STATS_COLS}

    aggregations = {**player_aggs, **match_aggs}

    return (
        pd
        # Need to sort df columns, because pandas freaks out if columns are in different order
        .concat(
            [
                home_stats[home_stats.columns.sort_values()],
                away_stats[away_stats.columns.sort_values()],
            ],
            sort=True,
        )
        .drop(["player_id", "player_name", "match_id"], axis=1)
        .groupby(["team", "year", "round_number", "oppo_team"])
        .aggregate(aggregations)
        .reset_index()
        .drop_duplicates(subset=["team", "year", "round_number"])
        .set_index(["team", "year", "round_number"], drop=False)
        .rename_axis([None, None, None])
    )
