import re
import pandas as pd
import numpy as np

DIGITS = re.compile(r"round\s+(\d+)$", flags=re.I)
QUALIFYING = re.compile(r"qualifying", flags=re.I)
ELIMINATION = re.compile(r"elimination", flags=re.I)
SEMI = re.compile(r"semi", flags=re.I)
PRELIMINARY = re.compile(r"preliminary", flags=re.I)
GRAND = re.compile(r"grand", flags=re.I)


class DataTransformer:
    def __init__(self, df):
        self.df = df.copy()

    def clean(
        self,
        min_year="01",
        max_year="2016",
        drop_cols=["venue", "crowd", "datetime", "season_round"],
    ):
        return (
            self.df[
                (self.df["datetime"] >= f"{min_year}-01-01")
                & (self.df["datetime"] <= f"{max_year}-12-31")
            ]
            .assign(round_number=self.__extract_round_number, year=self.__extract_year)
            .drop(drop_cols, axis=1)
        )

    def stack_teams(self, **kwargs):
        team_dfs = [self.__team_df("home", **kwargs), self.__team_df("away", **kwargs)]

        return pd.concat(team_dfs, join="inner").sort_index()

    def __extract_round_number(self, df):
        return df["season_round"].map(self.__match_round)

    def __match_round(self, round_string):
        digits = DIGITS.search(round_string)

        if digits is not None:
            return int(digits.group(1))
        if QUALIFYING.search(round_string) is not None:
            return 25
        if ELIMINATION.search(round_string) is not None:
            return 25
        if SEMI.search(round_string) is not None:
            return 26
        if PRELIMINARY.search(round_string) is not None:
            return 27
        if GRAND.search(round_string) is not None:
            return 28

        raise Exception(f"Round label {round_string} doesn't match any known patterns")

    def __team_df(self, team_type, **kwargs):
        df = self.clean(**kwargs)
        is_at_home = team_type == "home"
        oppo_team_type = "away" if is_at_home else "home"
        at_home_col = np.ones(len(df)) if is_at_home else np.zeros(len(df))

        return (
            df.rename(columns=self.__replace_col_names(team_type, oppo_team_type))
            .assign(at_home=at_home_col)
            .set_index(["team", "year", "round_number"], drop=False)
            .rename_axis([None, None, None])
            # Gotta drop duplicates, because St Kilda & Carlton tied a Grand Final
            # in 2010 and had to replay it, so let's just pretend that never happened
            .drop_duplicates(subset=["team", "year", "round_number"], keep="last")
        )

    @staticmethod
    def __replace_col_names(team_type, oppo_team_type):
        return lambda col_name: (
            col_name.replace(f"{team_type}_", "").replace(f"{oppo_team_type}_", "oppo_")
        )

    @staticmethod
    def __extract_year(df):
        return df["datetime"].map(lambda date_time: date_time.year)
