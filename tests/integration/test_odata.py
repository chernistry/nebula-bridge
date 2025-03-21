# tests/integration/test_odata.py
import pytest
from unittest.mock import patch
import requests
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


# ==== TEST: OData Longest Flight SUCCESS SCENARIO (REVISED) ==== #
@pytest.mark.integration
def test_odata_longest_flight_ok() -> None:
    """
    Verify that when the OData services respond successfully, the
    /odata-longest-flight endpoint returns the correct data.
    """
    mock_people_data = {
        "value": [
            {
                "FirstName": "Luke",
                "LastName": "Skywalker",
                "Flights": [
                    {"AirlineCode": "ANA", "Distance": 2200},  # Было 999, теперь 2200
                    {"AirlineCode": "BA", "Distance": 800},
                ],
            }
        ]
    }

    def side_effect(url, *args, **kwargs):
        if "People?" in url:
            return MockResponse200(mock_people_data)
        else:
            return MockResponse200({"value": []})

    with patch.object(requests, "get", side_effect=side_effect):
        response = client.get("/odata-longest-flight?use_mock=true")
        assert response.status_code == 200
        data = response.json()
        print("DEBUG RESPONSE:", data)  # DEBUG - посмотреть ответ сервиса
        assert "distance" in data, "Response missing 'distance' key"
        assert data["distance"] == 2200, f"Expected distance 2200, got {data['distance']}"
        assert "Luke Skywalker" in data["person"], "Incorrect person returned"

# ==== TEST: OData Longest Flight FAILURE SCENARIO (REVISED) ==== #
@pytest.mark.integration
def test_odata_longest_flight_fail() -> None:
    """
    Verify that if an error occurs during the OData request,
    the endpoint returns a 502 status code.

    In the rewritten logic, if a real fetch fails and no cache fallback is available,
    a 502 error is raised.
    """
    with patch.object(requests, "get", side_effect=requests.RequestException("Mocked OData error")):
        response = client.get("/odata-longest-flight")
        assert response.status_code == 502, f"Expected status 502, got {response.status_code}"


# ==== MOCK RESPONSE CLASS ==== #
class MockResponse200:
    """
    A simple mock response class to simulate successful HTTP responses.
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

