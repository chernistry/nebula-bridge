# tests/integration/test_etl.py
import pytest
import json
from unittest.mock import patch, AsyncMock

from app.etl import run_etl


# ==== TEST: ETL RUN IN DEV MODE (NO FILTERING) ==== #
@pytest.mark.integration
@pytest.mark.asyncio
async def test_run_etl_dev_mode() -> None:
    """
    Verify that in DEV mode the ETL process does not filter out 'The Phantom Menace'
    and returns all vehicle results.
    """
    # Patch configuration to set DEV mode
    with patch("app.config.USE_PROD", False):
        # Prepare mock data to avoid actual API calls.
        mock_data = {
            "results": [
                {"name": "Speeder", "pilots": [], "films": ["https://dev.film/2"]},
                {"name": "AT-AT", "pilots": [], "films": ["https://dev.film/3"]},
            ]
        }

        async_mock = AsyncMock(return_value=mock_data)
        with patch("app.etl.cached_get", async_mock):
            vehicles = await run_etl(use_wookiee=False, use_prod=False)

            assert len(vehicles) == 2
            assert vehicles[0].name == "Speeder"


# ==== TEST: ETL RUN IN PROD MODE WITH PHANTOM FILTER (FILM FOUND) ==== #
@pytest.mark.integration
@pytest.mark.asyncio
async def test_run_etl_prod_mode_phantom_filter() -> None:
    """
    Verify that in PROD mode the ETL process filters vehicles to include only those
    associated with 'The Phantom Menace' when the film is found.
    """
    # Data for vehicles and the phantom film lookup.
    prod_vehicle_data = {
        "results": [
            {
                "name": "Speeder PROD",
                "pilots": [],
                "films": ["https://apim.workato.com/films/1/"],
            },
            {
                "name": "Phantom Vehicle",
                "pilots": [],
                "films": ["https://apim.workato.com/films/4/"],
            },
        ]
    }

    phantom_film_data = {
        "results": [
            {
                "url": "https://apim.workato.com/films/4/",
            }
        ]
    }

    # The side_effect returns vehicle data first, then phantom film data.
    async_mock_cached_get = AsyncMock(side_effect=[prod_vehicle_data, phantom_film_data])
    with patch("app.config.USE_PROD", True):
        with patch("app.etl.cached_get", async_mock_cached_get):
            vehicles = await run_etl(use_wookiee=False, use_prod=True)

            # Only the vehicle linked to the phantom film should remain.
            assert len(vehicles) == 1
            assert vehicles[0].name == "Phantom Vehicle"


# ==== TEST: ETL RUN IN PROD MODE WHEN PHANTOM FILM NOT FOUND ==== #
@pytest.mark.integration
@pytest.mark.asyncio
async def test_run_etl_prod_mode_phantom_not_found() -> None:
    """
    Verify that if 'The Phantom Menace' film is not found in the API response,
    the ETL process logs a warning but does not filter out any vehicles.
    """
    prod_vehicle_data = {
        "results": [
            {"name": "Speeder PROD", "pilots": [], "films": ["https://apim.workato.com/films/1/"]},
            {"name": "Other film", "pilots": [], "films": ["https://apim.workato.com/films/999/"]},
        ]
    }

    # Phantom film data returns an empty result to indicate film not found.
    phantom_film_data = {"results": []}

    async_mock_cached_get = AsyncMock(side_effect=[prod_vehicle_data, phantom_film_data])
    with patch("app.config.USE_PROD", True):
        with patch("app.etl.cached_get", async_mock_cached_get):
            vehicles = await run_etl(use_wookiee=False, use_prod=True)

            # All vehicles should be returned if no filtering is applied.
            assert len(vehicles) == 2
