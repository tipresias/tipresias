import os
import sys
import re
import pandas as pd
import numpy as np

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../"))

if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

from scripts.data import raw_data


BETTING_LABEL = "afl_betting"
MATCH_LABEL = "ft_match_list"
BETTING_TEAM_TRANSLATIONS = {
    "Tigers": "Richmond",
    "Blues": "Carlton",
    "Demons": "Melbourne",
    "Giants": "GWS",
    "Suns": "Gold Coast",
    "Bombers": "Essendon",
    "Swans": "Sydney",
    "Magpies": "Collingwood",
    "Kangaroos": "North Melbourne",
    "Crows": "Adelaide",
    "Bulldogs": "Western Bulldogs",
    "Dockers": "Fremantle",
    "Power": "Port Adelaide",
    "Saints": "St Kilda",
    "Eagles": "West Coast",
    "Lions": "Brisbane",
    "Cats": "Geelong",
    "Hawks": "Hawthorn",
    "Adelaide Crows": "Adelaide",
    "Brisbane Lions": "Brisbane",
    "Gold Coast Suns": "Gold Coast",
    "GWS Giants": "GWS",
    "Geelong Cats": "Geelong",
    "West Coast Eagles": "West Coast",
    "Sydney Swans": "Sydney",
}
VENUE_TRANSLATIONS = {
    "AAMI": "AAMI Stadium",
    "ANZ": "ANZ Stadium",
    "Adelaide": "Adelaide Oval",
    "Aurora": "UTAS Stadium",
    "Aurora Stadium": "UTAS Stadium",
    "Blacktown": "Blacktown International",
    "Blundstone": "Blundstone Arena",
    "Cazaly's": "Cazaly's Stadium",
    "Domain": "Domain Stadium",
    "Etihad": "Etihad Stadium",
    "GMHBA": "GMHBA Stadium",
    "Gabba": "Gabba",
    "Jiangwan": "Jiangwan Stadium",
    "MCG": "MCG",
    "Mars": "Mars Stadium",
    "Metricon": "Metricon Stadium",
    "Perth": "Optus Stadium",
    "SCG": "SCG",
    "Spotless": "Spotless Stadium",
    "StarTrack": "Manuka Oval",
    "TIO": "TIO Stadium",
    "UTAS": "UTAS Stadium",
    "Westpac": "Westpac Stadium",
    "TIO Traegar Park": "TIO Stadium",
}
BETTING_COL_INDICES = [0, 1, 2, 3, 4, 5, 6, 7, 8]
COL_LABEL_ROW = 2
MATCH_COL_INDICES = [0, 1, 2, 3, 4, 5, 6, 7]
ROUND_REGEX = re.compile(r"(round\s+\d\d?|.*final.*)", flags=re.I)
MATCH_STATUSES = ["BYE", "MATCH CANCELLED"]
HOME_INDEX = 0
AWAY_INDEX = 1
HOME_V_AWAY_INDEX = 2
HOME_V_AWAY_LABELS = ["home_team", "v", "away_team"]


def translate_venue(venue):
    return VENUE_TRANSLATIONS[venue] if venue in VENUE_TRANSLATIONS.keys() else venue


def translate_date(df):
    # year is a float, so we have to convert it to int, then str to concatenate
    # with the date string (date parser doesn't recognize years as floats)
    return df["date"].astype(str) + " " + df["year"].astype(int).astype(str)


def translate_score(idx):
    return (
        lambda scores: float(scores[idx])
        if isinstance(scores, list) and len(scores) == 2
        else None
    )


def get_score(idx):
    return lambda df: df["result"].str.split("-").map(translate_score(idx))


def translate_home_team(df):
    return df["home_team"].map(lambda x: None if x in MATCH_STATUSES else x)


def get_season_round(df):
    # Round label just appears at top of round in table,
    # so forward fill to apply it to all relevant matches
    return df["date"].str.extract(ROUND_REGEX, expand=True).ffill()


def clean_match_data(data):
    # Ignore useless columns that are result of BeautifulSoup table parsing
    df = pd.DataFrame(data).iloc[:, MATCH_COL_INDICES]
    # First column is year inserted during scraping
    column_labels = (
        df.loc[COL_LABEL_ROW, :].astype(str).str.lower().str.replace(" ", "_").values
    )
    # Data rows split <home team> v <away team> into 3 columns, but label rows use 1 column,
    # so we have to split labels manually
    expanded_column_labels = (
        ["year"],
        [column_labels[HOME_V_AWAY_INDEX - 1]],
        HOME_V_AWAY_LABELS,
        column_labels[HOME_V_AWAY_INDEX + 1 : -(len(HOME_V_AWAY_LABELS) - 1)],
    )
    df.columns = np.concatenate(expanded_column_labels)

    # We need to do this in two steps because there's at least one case of the website's data table
    # being poorly organised, leading to specious duplicates.
    # So, we fill the season_round column before dropping duplicates, then we assign home_score,
    # away_score, and date to avoid NaNs that will raise errors.
    return (
        df.assign(
            season_round=get_season_round,
            home_team=translate_home_team,
            venue=df["venue"].map(translate_venue),
        )
        # Check all columns except for round #, because round # would make all rows unique.
        # Duplicate rows are from table labels/headers that are not useful
        .drop_duplicates(subset=df.columns.values[:-1], keep=False)
        # The only rows with NaNs are the round label rows that we no longer need
        .dropna()
        # Result column has format: 'home_score-away_score'
        .assign(
            home_score=get_score(HOME_INDEX),
            away_score=get_score(AWAY_INDEX),
            date=translate_date,
        )
        .drop(["result", "year", "v"], axis=1)
        .reset_index(drop=True)
    )


def translate_betting_teams(df):
    return df["team"].map(
        lambda x: BETTING_TEAM_TRANSLATIONS[x]
        if x in BETTING_TEAM_TRANSLATIONS.keys()
        else x
    )


def clean_betting_data(data):
    # Ignore useless columns that are result of BeautifulSoup table parsing
    df = pd.DataFrame(data).iloc[:, BETTING_COL_INDICES]
    df.columns = (
        df.loc[COL_LABEL_ROW, :].map(lambda x: x.lower().replace(" ", "_")).rename(None)
    )

    df = (
        df.assign(
            team=translate_betting_teams,
            date=lambda x: x["date"].ffill(),
            venue=df["venue"].ffill().map(translate_venue),
        )
        .dropna()
        # Duplicate rows are from table labels/headers that are not useful, so remove all
        .drop_duplicates(keep=False)
        .reset_index(drop=True)
        # Save date parsing till the end to avoid ValueErrors
        # .assign(date=lambda x: x['date'].apply(dateutil.parser.parse))
        .drop(["score", "win_paid", "margin", "line_paid"], axis=1)
    )

    if len(df) % 2 != 0:
        raise Exception(
            f"Betting DataFrame should have an even number of rows, but has {len(df)} instead"
        )

    return df.assign(home=([1, 0] * int(len(df) / 2)))


def main(data, csv=False):
    dfs = []

    for key, value in data.items():
        if key == BETTING_LABEL:
            df = clean_betting_data(value)
        if key == MATCH_LABEL:
            df = clean_match_data(value)

        if csv:
            data_directory = os.path.join(BASE_DIR, "data")

            if not os.path.isdir(data_directory):
                os.makedirs(data_directory)

            df.to_csv(os.path.join(data_directory, f"{key}.csv"), index=False)

        dfs.append(df)

    return tuple(dfs)


if __name__ == "__main__":
    main(raw_data.main(), csv=True)
