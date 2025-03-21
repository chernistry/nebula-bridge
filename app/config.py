import os
from dotenv import load_dotenv



# ==== LOAD ENVIRONMENT VARIABLES ==== #

# Load environment variables from the .env file at module import.
load_dotenv()



# ==== CONFIGURATION CONSTANTS ==== #

# Default URLs read from the environment. These can be overridden in tests by
# setting os.environ["DEV_BASE_URL"] or os.environ["PROD_BASE_URL"].
DEV_BASE_URL = os.getenv("DEV_BASE_URL", "https://swapi.dev/api")
PROD_BASE_URL = os.getenv("PROD_BASE_URL", "https://mocked-up-url-for-test.com")

API_TOKEN = os.getenv("API_TOKEN")

# Configure SQLite usage based on environment variables.
USE_SQLITE = os.getenv("USE_SQLITE", "true").lower() in ["true", "1"]
SQLITE_PATH = os.getenv("SQLITE_PATH", "app/load/database.db")
SQLITE_PATH_DEV = os.getenv("SQLITE_PATH_DEV", "app/load/dev_database.db")

# Dynamically choose the database path based on the USE_PROD setting.
if os.getenv("USE_PROD", "false").lower() in ["true", "1"]:
    DB_PATH = SQLITE_PATH
else:
    DB_PATH = SQLITE_PATH_DEV

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost")
WOOKIE_MODE = os.getenv("WOOKIE_MODE", "false").lower() in ["true", "1"]



# ==== HELPER FUNCTIONS ==== #

def get_base_url(force_prod: bool = False) -> str:
    """
    Retrieve the base URL from the environment.

    If force_prod is True, the production URL is returned regardless of other settings.
    Otherwise, the function checks the 'USE_PROD' environment variable to determine which
    base URL to return.

    Args:
        force_prod (bool): If True, always returns the production base URL.

    Returns:
        str: The selected base URL.
    """
    if force_prod:
        return PROD_BASE_URL

    if os.getenv("USE_PROD", "false").lower() in ["true", "1"]:
        return PROD_BASE_URL

    return DEV_BASE_URL



def __getattr__(name):
    """
    Provide dynamic module-level attributes on demand.

    This function supports dynamic resolution of attributes like 'USE_PROD', so that
    patching app.config.USE_PROD in tests is recognized.

    Args:
        name (str): The name of the attribute being accessed.

    Returns:
        Any: The value of the attribute if recognized.

    Raises:
        AttributeError: If the attribute is not defined.
    """
    if name == "USE_PROD":
        return os.getenv("USE_PROD", "false").lower() in ["true", "1"]
    raise AttributeError(f"module {__name__} has no attribute {name}")
