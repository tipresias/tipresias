import sys

from project.settings.common import BASE_DIR

if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)
