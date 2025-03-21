# tests/test_main_endpoints.py
import pytest
from unittest.mock import patch
import requests
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)



# ==== TEST: RUN ETL ENDPOINT ==== #
@pytest.mark.integration
def test_run_etl_endpoint() -> None:
    """
    Test the /run-etl endpoint by directly calling it via TestClient while
    mocking potential API calls within the ETL process.

    Expected behavior:
      - The endpoint should return a 200 status code.
      - The JSON response must contain a "vehicles" key with one vehicle
        whose name is "MockVehicle".
    """
    with patch("app.etl.cached_get") as mock_cached_get:
        mock_cached_get.return_value = {"results": [{"name": "MockVehicle"}]}
        response = client.get("/run-etl?use_wookiee=false")
        assert response.status_code == 200

        data = response.json()
        assert "vehicles" in data
        assert len(data["vehicles"]) == 1
        assert data["vehicles"][0]["name"] == "MockVehicle"



# ==== TEST: EXTRACT VEHICLES PHANTOM ENDPOINT ==== #
@pytest.mark.integration
def test_extract_vehicles_phantom() -> None:
    """
    Test the /extract-vehicles-phantom endpoint to verify that previously
    stored vehicles can be retrieved from the database.

    Expected behavior:
      - The endpoint should return a 200 status code.
      - The JSON response must contain a "vehicles" key.
      - If vehicles exist, each vehicle should include a "name" key.
    """
    response = client.get("/extract-vehicles-phantom")
    assert response.status_code == 200

    data = response.json()
    assert "vehicles" in data

    # If vehicles are present, verify that each has the "name" key.
    if data["vehicles"]:
        assert "name" in data["vehicles"][0]



# ==== TEST: SEARCH CHARACTERS ENDPOINT (BLOCKED IN DEV MODE) ==== #
@pytest.mark.integration
def test_search_characters_prod_block() -> None:
    """
    Test that when USE_PROD is false, the /search-characters-prod endpoint
    returns a 403 status code.
    """
    with patch("app.config.USE_PROD", False):
        response = client.get("/search-characters-prod?query=Grievous")
        assert response.status_code == 403



# ==== TEST: SEARCH CHARACTERS ENDPOINT (PROD MODE) ==== #
@pytest.mark.integration
def test_search_characters_prod_ok() -> None:
    """
    Simulate production mode and verify that the /search-characters-prod endpoint
    returns the expected character data after mocking the external API response.

    Expected behavior:
      - The endpoint should return a 200 status code.
      - The JSON response must contain a "characters" key.
      - The first character's name should be "Grievous Clone".
    """
    with patch("app.config.USE_PROD", True):
        with patch.object(
                requests, "get", return_value=MockResponse200({
                    "results": [
                        {
                            "name": "Grievous Clone",
                            "films": ["film1", "film2"],
                            "species": [],
                            "edited": "2021-01-01"
                        }
                    ]
                })
        ):
            response = client.get("/search-characters-prod?query=Grievous")
            assert response.status_code == 200

            data = response.json()
            assert "characters" in data
            assert data["characters"][0]["name"] == "Grievous Clone"



# ==== MOCK RESPONSE CLASS ==== #
class MockResponse200:
    """
    A simple mock response class to simulate a successful HTTP response.
    """

    def __init__(self, json_data: dict) -> None:
        self._json_data = json_data
        self.status_code = 200

    def json(self) -> dict:
        """
        Return the mocked JSON data.
        """
        return self._json_data

    def raise_for_status(self) -> None:
        """
        Simulate a successful response by doing nothing.
        """
        pass
