import pandas as pd
import numpy as np

TEAM_LEVEL = 0
YEAR_LEVEL = 1
WIN_POINTS = 4
AVG_SEASON_LENGTH = 23


class FeatureBuilder:
    def __init__(self, df):
        self.df = df.copy()

        wins = (df["score"] > df["oppo_score"]).astype(int)
        draws = (df["score"] == df["oppo_score"]).astype(int) * 0.5
        self._last_week_results = (wins + draws).groupby(level=TEAM_LEVEL).shift()

    def transform(self):
        self.add_last_week_score()
        self.add_season_cum_features()
        self.add_rolling_features()
        self.add_ladder_position()
        self.add_win_streak()

    # Group by team (not team & year) to get final score from previous season for round 1.
    # This reduces number of rows that need to be dropped and prevents a 'cold start'
    # for cumulative features
    def add_last_week_score(self):
        self.df.loc[:, "last_week_score"] = self.df.groupby(level=TEAM_LEVEL)[
            "score"
        ].shift()
        self.df.loc[:, "last_week_oppo_score"] = self.df.groupby(level=TEAM_LEVEL)[
            "oppo_score"
        ].shift()

    def add_season_cum_features(self, oppo_col=True):
        self.df.loc[:, "cum_percent"] = self.__cum_percent_col()
        self.df.loc[:, "cum_win_points"] = self.__cum_win_points_col()

        if oppo_col:
            self.__add_oppo_col("cum_percent")
            self.__add_oppo_col("cum_win_points")

    def add_rolling_features(self, oppo_col=True):
        self.df.loc[:, "rolling_pred_win_rate"] = self.__rolling_pred_win_rate_col()
        self.df.loc[
            :, "rolling_last_week_win_rate"
        ] = self.__rolling_last_week_win_rate_col()

        if oppo_col:
            self.__add_oppo_col("rolling_pred_win_rate")
            self.__add_oppo_col("rolling_last_week_win_rate")

    def add_ladder_position(self, oppo_col=True):
        if "cum_win_points" or "cum_percent" not in self.df.columns:
            self.add_season_cum_features(oppo_col=oppo_col)

        self.df.loc[:, "ladder_position"] = self.__ladder_position_col()

        if oppo_col:
            self.__add_oppo_col("ladder_position")

    def add_win_streak(self, oppo_col=True):
        self.df.loc[:, "win_streak"] = self.__win_streak_col()

        if oppo_col:
            self.__add_oppo_col("win_streak")

    def __cum_percent_col(self):
        if "last_week_score" or "last_week_oppo_score" not in self.df.columns:
            self.add_last_week_score()

        return self.__cum_col(self.df["last_week_score"]) / self.__cum_col(
            self.df["last_week_oppo_score"]
        )

    def __cum_win_points_col(self):
        return self.__cum_col(self._last_week_results * WIN_POINTS)

    def __rolling_pred_win_rate_col(self):
        predicted_results = self.df["line_odds"] < 0 + (self.df["line_odds"] == 0 * 0.5)

        return self.__rolling_col(predicted_results)

    def __rolling_last_week_win_rate_col(self):
        last_week_results = self._last_week_results

        return self.__rolling_col(last_week_results)

    def __ladder_position_col(self):
        # Pivot to get round-by-round match points and cumulative percent
        ladder_pivot_table = self.df[["cum_win_points", "cum_percent"]].pivot_table(
            index=["year", "round_number"],
            values=["cum_win_points", "cum_percent"],
            columns="team",
            aggfunc={"cum_win_points": np.sum, "cum_percent": np.mean},
        )

        # To get round-by-round ladder ranks, we sort each round by win points & percent,
        # then save index numbers
        ladder_index = []
        ladder_values = []

        for year_round_idx, round_row in ladder_pivot_table.iterrows():
            sorted_row = round_row.unstack(level=TEAM_LEVEL).sort_values(
                ["cum_win_points", "cum_percent"], ascending=False
            )

            for ladder_idx, team_name in enumerate(sorted_row.index.get_values()):
                ladder_index.append(tuple([team_name, *year_round_idx]))
                ladder_values.append(ladder_idx + 1)

        ladder_multi_index = pd.MultiIndex.from_tuples(
            ladder_index, names=("team", "year", "round_number")
        )
        return pd.Series(
            ladder_values, index=ladder_multi_index, name="ladder_position"
        )

    # Calculate win/loss streaks. Positive result (win or draw) adds 1 (or 0.5);
    # negative result subtracts 1. Changes in direction (i.e. broken streak) result in
    # starting at 1 or -1.
    def __win_streak_col(self):
        last_week_win_groups = self._last_week_results.groupby(
            level=TEAM_LEVEL, group_keys=False
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
                    raise ValueError(
                        f"No results should be negative, but {result} is at index {idx}"
                        f" of group {team_group_key}"
                    )
                else:
                    streaks.append(0)

            streak_groups.extend(streaks)

        return pd.Series(streak_groups, index=self.df.index)

    # Get cumulative stats by team & year
    @staticmethod
    def __cum_col(series):
        return (
            series.groupby(level=[TEAM_LEVEL, YEAR_LEVEL])
            .cumsum()
            .rename(f"cum_{series.name}")
        )

    @staticmethod
    def __rolling_col(series):
        groups = series.groupby(level=TEAM_LEVEL, group_keys=False)
        # Using mean season length (23) for rolling window due to a combination of
        # testing different window values for a previous model and finding 23 to be
        # a good window for data vis.
        # Not super scientific, but it works well enough.
        rolling_win_rate = groups.rolling(window=AVG_SEASON_LENGTH).mean()
        # Only select rows that are NaNs in rolling series
        expanding_win_rate = groups.expanding(1).mean()[rolling_win_rate.isna()]

        return (
            pd.concat([rolling_win_rate, expanding_win_rate], join="inner")
            .dropna()
            .sort_index()
            .rename(f"rolling_{series.name}_23")
        )

    def __add_oppo_col(self, col_name):
        col_translations = {"oppo_team": "team"}
        # col_translations[col_name] = f'oppo_{col_name}'

        oppo_col = (
            self.df.loc[:, ["year", "round_number", "oppo_team", col_name]]
            # We switch out oppo_team for team in the index,
            # then assign feature as oppo_{feature_column}
            .rename(columns=col_translations)
            .set_index(["team", "year", "round_number"])
            .sort_index()
        )

        self.df.loc[:, f"oppo_{col_name}"] = oppo_col[col_name]

        return oppo_col[col_name]
