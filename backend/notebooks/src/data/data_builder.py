import pandas as pd


class DataBuilder:
    def __init__(
        self,
        data_classes,
        csv_paths,
        shared_index_cols=["date", "venue", "home_team", "away_team"],
    ):
        if len(csv_paths) != len(data_classes):
            raise ValueError("csv_paths and data_classes arguments must be same length")

        self.dfs = [
            data_class(csv_paths[idx], shared_index_cols).data_frame()
            for idx, data_class in enumerate(data_classes)
        ]

    def concat(self, raw=False):
        if raw:
            return pd.concat([self.dfs], axis=1)

        return pd.concat(self.dfs, axis=1).dropna().reset_index().drop("date", axis=1)


class BettingData:
    def __init__(
        self,
        csv_path,
        shared_index_cols,
        index_col=("date", "venue"),
        parse_dates=["date"],
    ):
        self.shared_index_cols = shared_index_cols
        self.index_col = index_col
        self._data = pd.read_csv(csv_path, index_col=index_col, parse_dates=parse_dates)

    def data_frame(self):
        home_df, away_df = (
            self.__split_home_away("home"),
            self.__split_home_away("away"),
        )

        return (
            home_df.merge(away_df, on=self.index_col)
            .reset_index()
            .set_index(self.shared_index_cols)
        )

    def __split_home_away(self, team_type):
        return (
            self._data[self._data["home"] == int(team_type == "home")]
            .drop("home", axis=1)
            .rename(columns=self.__rename_home_away_columns(team_type))
        )

    def __rename_home_away_columns(self, team_type):
        return lambda column_name: f"{team_type}_{column_name}"


class MatchData:
    def __init__(self, csv_path, shared_index_cols, parse_dates=["date"]):
        self.shared_index_cols = shared_index_cols
        self._data = pd.read_csv(csv_path, parse_dates=parse_dates)

    def data_frame(self):
        return (
            self._data.rename(columns={"date": "datetime"})
            .assign(date=self.__convert_datetime_to_date)
            .set_index(self.shared_index_cols)
        )

    def __convert_datetime_to_date(self, df):
        return df["datetime"].map(lambda date_time: date_time.date())
