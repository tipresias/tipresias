from server import data_import

CONFIG = data_import.fetch_data_config()

TEAM_NAMES = CONFIG["team_names"]
DEFUNCT_TEAM_NAMES = CONFIG["defunct_team_names"]
VENUES = CONFIG["venues"]
