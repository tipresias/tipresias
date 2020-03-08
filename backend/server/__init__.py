"""Only Django 'app' in the project. Contains all core functionality."""

import os
import sys

PROJECT_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../"))

if PROJECT_PATH not in sys.path:
    sys.path.append(PROJECT_PATH)
