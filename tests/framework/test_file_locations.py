import os
import sys

project_path = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '../../'))

if project_path not in sys.path:
    sys.path.append(project_path)

from config import application


def test_env_file_exists():
    ''' Test should be True if wsgi.py file is present '''
    assert os.path.exists(os.path.join(
        application.BASE_DIRECTORY, 'wsgi.py')), 'App startup file should exist'
