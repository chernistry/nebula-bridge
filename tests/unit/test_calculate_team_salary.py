import json
from app.main import calculate_team_salaries


def main() -> None:
    """
    Executes a test of the calculate_team_salaries function using sample data.

    This test verifies that the function computes the total team salaries correctly
    for a given list of employee records. The expected output is compared with the
    function's result, and a message is printed indicating whether the test passed.

    Expected behavior:
      - For manager with id 1, the total salary should be 1000 + 800 + 600 + 400 + 300 + 500.
      - For manager with id 7, the total salary should be 1200 + 400.
    """
    # Sample employee data simulating an API response
    employees = [
        {"id": 1, "manager_id": None, "salary": 1000},
        {"id": 2, "manager_id": 1, "salary": 800},
        {"id": 3, "manager_id": 1, "salary": 600},
        {"id": 4, "manager_id": 2, "salary": 400},
        {"id": 5, "manager_id": 2, "salary": 300},
        {"id": 6, "manager_id": 3, "salary": 500},
        {"id": 7, "manager_id": None, "salary": 1200},  # Separate top-level manager
        {"id": 8, "manager_id": 7, "salary": 400},        # Subordinate of another top manager
    ]

    # Calculate team salaries based on the provided employee data
    result = calculate_team_salaries(employees)

    # Define the expected result for verification
    expected_result = {
        1: 1000 + 800 + 600 + 400 + 300 + 500,  # Manager 1 plus his team
        7: 1200 + 400,                        # Manager 7 plus subordinate
    }

    # Verify that the computed result matches the expected output
    assert result == expected_result, (
        f"Test failed! Expected {expected_result}, got {result}"
    )

    print("✅ Test passed!")


if __name__ == "__main__":
    main()
