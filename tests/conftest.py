import os
import app.config as config
from fastapi.testclient import TestClient
from app.main import app

# --- Override Environment Variables for Testing ---

# Use a local, relative SQLite file (writable in the test context)
os.environ["SQLITE_PATH"] = "test_database.db"
# Override REDIS_URL to avoid trying to resolve Docker service names
os.environ["REDIS_URL"] = "redis://localhost:6379"
# Optionally, set USE_PROD to true or false as needed for your tests
os.environ["USE_PROD"] = "true"

# Force the DB_PATH in the config to use the new SQLITE_PATH value
config.DB_PATH = os.environ["SQLITE_PATH"]

# Ensure the test database file is removed if it exists, so we start fresh.
if os.path.exists("test_database.db"):
    os.remove("test_database.db")

# --- Patch the Redis Client ---

# Define a dummy Redis client that always returns None (forcing cache misses)
class DummyRedis:
    def get(self, key):
        return None
    def setex(self, key, ttl, value):
        # Do nothing
        pass

# Overwrite the module-level _redis_client in app.main with our dummy client.
import app.main as main_module
main_module._redis_client = DummyRedis()

# --- Create a TestClient Fixture ---
import pytest

@pytest.fixture(scope="session")
def client() -> TestClient:
    """
    Creates and returns a TestClient instance for the entire test session.
    """
    with TestClient(app) as test_client:
        yield test_client
