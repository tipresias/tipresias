import re
import pandas as pd
import numpy as np

DIGITS = re.compile(r'round\s+(\d+)$', flags=re.I)
QUALIFYING = re.compile(r'qualifying', flags=re.I)
ELIMINATION = re.compile(r'elimination', flags=re.I)
SEMI = re.compile(r'semi', flags=re.I)
PRELIMINARY = re.compile(r'preliminary', flags=re.I)
GRAND = re.compile(r'grand', flags=re.I)
REQUIRED_COLUMNS = ['venue', 'crowd', 'datetime', 'season_round']


class DataCleaner():
    def __init__(self, min_year=1, max_year=2016, drop_cols=['venue', 'crowd']):
        self.min_year = min_year
        self.max_year = max_year
        self.drop_cols = drop_cols

    # data_frame must have the following columns to be valid:
    # venue, crowd, datetime, season_round
    def transform(self, data_frame):
        if type(data_frame) is not pd.DataFrame:
            raise TypeError(f'Must receive a pandas DataFrame as an argument, '
                            'but got {type(data_frame)} instead.')

        if any((req_col not in data_frame.columns for req_col in REQUIRED_COLUMNS)):
            raise ValueError(f"data_frame argument must have the columns 'venue', "
                             "'crowd', 'datetime', 'season_round', but the columns "
                             "given are {data_frame.columns.values}")

        df = data_frame.copy()

        return (df[(df['datetime'] >= f'{self.min_year}-01-01') & (df['datetime'] <= f'{self.max_year}-12-31')]
                .assign(round_number=self.__extract_round_number,
                        year=self.__extract_year)
                .drop(self.drop_cols + ['datetime', 'season_round'], axis=1))

    def __extract_round_number(self, df):
        return df['season_round'].map(self.__match_round)

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

        raise ValueError(
            f"Round label {round_string} doesn't match any known patterns")

    def __extract_year(self, df):
        return df['datetime'].map(lambda date_time: date_time.year)
