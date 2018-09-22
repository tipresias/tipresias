import os
import sys
from datetime import datetime
import dateutil
from urllib.parse import urljoin
import requests
from bs4 import BeautifulSoup
import numpy as np

project_path = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '../../'))
if project_path not in sys.path:
    sys.path.append(project_path)


BETTING_LABEL = 'afl_betting'
MATCH_LABEL = 'ft_match_list'
URL = 'https://www.footywire.com/afl/footy/'
PAGES = [BETTING_LABEL, MATCH_LABEL]


def match_row(year, tr):
    table_row = list(tr.stripped_strings)

    if len(table_row) == 0:
        return []

    return [year] + table_row


def match_table(year, data_div):
    data_table = data_div.find('table')

    if data_table is None:
        return None

    return [match_row(year, tr) for tr in data_table.find_all('tr')]


def betting_row(tr):
    table_row = list(tr.stripped_strings)

    # First two columns in data rows have rowspan="2", so empty cells need to be prepended
    # to every-other data row. There doesn't seem to be a good way of identifying these rows
    # apart from their length: 11 cells means the date is in the row, 9 means there's no date.
    # Also have to check for attributes, because column label rows have 9 items but no attributes.
    if len(table_row) == 9 and len(tr.attrs) > 0:
        return ([np.nan] * 2) + table_row

    return table_row


def betting_table(data_div):
    # afl_betting page nests the data table inside of an outer table
    data_table = data_div.find('table').find('table')

    if data_table is None:
        return None

    return [betting_row(tr) for tr in data_table.find_all('tr')]


def fetch_page(page_path, year):
    page_url = urljoin(URL, page_path)
    res = requests.get(page_url, params={'year': str(year)})
    text = res.text
    # Have to use html5lib, because default HTML parser wasn't working for this site
    return BeautifulSoup(text, 'html5lib')


def scrape_pages(page_path):
    today = datetime.now()
    data = []

    # Data for each season are on different pages, so looping back through years
    # until no data is returned.
    # NOTE: This can't be refactored, because we need to be able to break the loop
    # once a blank page is returned.
    for year in reversed(range(today.year + 1)):
        page = fetch_page(page_path, year)
        data_div = page.find('div', class_='datadiv')

        if data_div is None:
            break

        if page_path == BETTING_LABEL:
            data.extend(betting_table(data_div))
        if page_path == MATCH_LABEL:
            data.extend(match_table(year, data_div))

    if len(data) > 0:
        max_length = len(max(data, key=len))
        # Add null cells, so all rows are same length for Pandas dataframe
        padded_data = [list(row) + [None] * (max_length - len(row))
                       for row in data]
    else:
        padded_data = []

    return padded_data


def main():
    return {page_path: scrape_pages(page_path) for page_path in PAGES}


if __name__ == '__main__':
    main()
