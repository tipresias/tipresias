import os
import pandas as pd
import numpy as np
import dateutil
from datetime import datetime
import re

TEAM_TRANSLATION = {
    'Tigers': 'Richmond',
    'Blues': 'Carlton',
    'Demons': 'Melbourne',
    'Giants': 'GWS',
    'Suns': 'Gold Coast',
    'Bombers': 'Essendon',
    'Swans': 'Sydney',
    'Magpies': 'Collingwood',
    'Kangaroos': 'North Melbourne',
    'Crows': 'Adelaide',
    'Bulldogs': 'Footscray',
    'Dockers': 'Fremantle',
    'Power': 'Port Adelaide',
    'Saints': 'St Kilda',
    'Eagles': 'West Coast',
    'Lions': 'Brisbane Lions',
    'Cats': 'Geelong',
    'Hawks': 'Hawthorn'
}
VENUE_TRANSLATION = {
    'AAMI': 'Football Park',
    'ANZ': 'Stadium Australia',
    'Adelaide': 'Adelaide Oval',
    'Aurora': 'York Park',
    'Blacktown': 'Blacktown',
    'Blundstone': 'Bellerive Oval',
    "Cazaly's": "Cazaly's Stadium",
    'Domain': 'Subiaco',
    'Etihad': 'Docklands',
    'GMHBA': 'Kardinia Park',
    'Jiangwan': 'Jiangwan Stadium',
    'MCG': 'M.C.G',
    'Mars': 'Eureka Stadium',
    'Metricon': 'Carrara',
    'Perth': 'Perth Stadium',
    'SCG': 'S.C.G',
    'Spotless': 'Sydney Showground',
    'StarTrack': 'Manuka Oval',
    'TIO': 'Marrara Oval',
    'UTAS': 'York Park',
    'Westpac': 'Wellington',
    'TIO Traegar Park': 'Traeger Park'
}
BETTING_COL_INDICES = [0, 1, 2, 3, 4, 5, 6, 7, 8]
COL_LABEL_ROW = 2


def translate_teams(df):
    return df['team'].map(lambda x: TEAM_TRANSLATION[x] if x in TEAM_TRANSLATION.keys() else x)


def translate_venues(df):
    return df['venue'].ffill().map(lambda x: VENUE_TRANSLATION[x] if x in VENUE_TRANSLATION.keys() else x)


def clean_betting_data(data):
    # Ignore useless columns that are result of BeautifulSoup table parsing
    df = pd.DataFrame(data).iloc[:, BETTING_COL_INDICES]
    df.columns = df.loc[COL_LABEL_ROW, :].map(lambda x: x.lower().replace(' ', '_')).rename(None)

    df = (df.assign(team=translate_teams,
                    date=lambda x: x['date'].ffill(),
                    venue=translate_venues)
            .dropna()
            # Duplicate rows are from table labels/headers that are not useful, so remove all
            .drop_duplicates(keep=False)
            .reset_index(drop=True)
            # Save date parsing till the end to avoid ValueErrors
            .assign(date=lambda x: x['date'].apply(dateutil.parser.parse))
            .drop(['score', 'win_paid', 'margin', 'line_paid'], axis=1))

    return df


def main(data, csv=False):
    df = clean_betting_data(data)

    if csv:
        project_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../'))
        data_directory = os.path.join(project_path, 'data')

        if not os.path.isdir(data_directory):
            os.makedirs(data_directory)

        df.to_csv(os.path.join(data_directory, 'afl_betting.csv'), index=False)

    return df
