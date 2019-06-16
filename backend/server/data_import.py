"""Module for functions that fetch data"""

from typing import Tuple, Optional

import pandas as pd

from machine_learning import api


def fetch_prediction_data(
    year_range: Tuple[int, int], round_number: Optional[int] = None, verbose=1
) -> pd.DataFrame:
    """
    Fetch prediction data from machine_learning module

    Args:
        year_range (Tuple(int, int)): Min (inclusive) and max (exclusive) years
            for which to fetch data.
        round_number (int): Specify a particular round for which to fetch data.
        verbose (0 or 1): Whether to print info messages while fetching data.

    Returns:
        List of prediction data dictionaries
    """

    return pd.DataFrame(
        api.make_predictions(year_range, round_number=round_number, verbose=verbose)
    )


def fetch_fixture_data(
    start_date: str, end_date: str, verbose: int = 1
) -> pd.DataFrame:
    """
    Fetch fixture data (doesn't include match results) from machine_learning module.

    Args:
        start_date (str): Stringified date of form yyy-mm-dd that determines
            the earliest date for which to fetch data.
        end_date (str): Stringified date of form yyy-mm-dd that determines
            the latest date for which to fetch data.
        verbose (0 or 1): Whether to print info messages while fetching data.

    Returns:
        pandas.DataFrame with fixture data.
    """

    return pd.DataFrame(api.fetch_fixture_data(start_date, end_date, verbose=verbose))


def fetch_match_results_data(
    start_date: str, end_date: str, verbose: int = 1
) -> pd.DataFrame:
    """
    Fetch results data for past matches from machine_learning module.

    Args:
        start_date (str): Stringified date of form yyy-mm-dd that determines
            the earliest date for which to fetch data.
        end_date (str): Stringified date of form yyy-mm-dd that determines
            the latest date for which to fetch data.
        verbose (0 or 1): Whether to print info messages while fetching data.

    Returns:
        pandas.DataFrame with fixture data.
    """

    return pd.DataFrame(
        api.fetch_match_results_data(start_date, end_date, verbose=verbose)
    )
