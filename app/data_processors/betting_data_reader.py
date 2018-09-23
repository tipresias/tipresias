import os
import pandas as pd

project_path = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '../../'))


class BettingDataReader():
    def __init__(self, filename='afl_betting.csv', index_cols=('date', 'venue'),
                 parse_dates=['date']):
        pass
