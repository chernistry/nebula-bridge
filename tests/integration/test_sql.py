import pytest
from unittest.mock import patch
import requests
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


# ==== TEST: CALCULATE TEAM SALARY SUCCESS SCENARIO (REVISED) ==== #
@pytest.mark.integration
def test_calculate_team_salary_ok() -> None:
    """
    Verify that the /calculate-team-salary endpoint returns the expected
    team_salaries structure when the external API responds correctly.

    Expected behavior:
      - Employee 1 manages Employee 2: total salary for Employee 1 should be 1800.
      - Employee 3, with no subordinates, should have a total salary of 500.
    """
    # Update mock data to use the expected key names.
    mock_emp_data = {
        "employees": [
            {"EmployeeID": "1", "Salary": "1000", "ManagerID": None},
            {"EmployeeID": "2", "Salary": "800", "ManagerID": "1"},
            {"EmployeeID": "3", "Salary": "500", "ManagerID": None},
        ]
    }

    with patch.object(requests, "get", return_value=MockResponse200(mock_emp_data)):
        response = client.get("/calculate-team-salary")
        assert response.status_code == 200, f"Expected 200 OK, got {response.status_code}"
        data = response.json()
        assert "team_salaries" in data, "Response missing 'team_salaries' key"

        # Build a dictionary of salaries by employee ID.
        salaries = {r["id"]: r["TotalTeamSalary"] for r in data["team_salaries"]}
        assert salaries[1] == 1800, f"Expected total salary 1800 for employee 1, got {salaries[1]}"
        assert salaries[3] == 500, f"Expected total salary 500 for employee 3, got {salaries[3]}"


# ==== TEST: CALCULATE TEAM SALARY FAILURE SCENARIO ==== #
@pytest.mark.integration
def test_calculate_team_salary_api_fail() -> None:
    """
    Verify that the /calculate-team-salary endpoint returns a 500 status code
    when the external API request to /api/get_employees fails.
    """
    with patch.object(requests, "get", side_effect=Exception("Mocked error")):
        response = client.get("/calculate-team-salary")
        assert response.status_code == 500, f"Expected 500 Internal Server Error, got {response.status_code}"


# ==== MOCK RESPONSE CLASS (REUSED) ==== #
class MockResponse200:
    """
    A mock response class to simulate a successful HTTP response.
    """
    def __init__(self, json_data: dict) -> None:
        self._json_data = json_data
        self.status_code = 200

    def json(self) -> dict:
        """
        Returns the provided JSON data.
        """
        return self._json_data

    def raise_for_status(self) -> None:
        """
        Simulate a successful response by doing nothing.
        """
        pass





