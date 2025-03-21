import pytest
import json
import asyncio
from unittest.mock import patch, AsyncMock

from app.extract.api_client import (
    fetch_data,
    cached_get,
    parallel_cached_get,
    get_redis,
)


# ==== TEST: fetch_data SUCCESS SCENARIO ==== #

@pytest.mark.integration
@pytest.mark.asyncio
async def test_fetch_data_ok() -> None:
    """
    Test that fetch_data returns the expected JSON response when
    aiohttp.ClientSession().get is successfully mocked.
    """
    # Create a mock response for the GET request
    async_mock_response = AsyncMock()
    async_mock_response.status = 200
    async_mock_response.raise_for_status = AsyncMock()
    async_mock_response.json = AsyncMock(return_value={"mock_key": "mock_value"})

    # Create a mock session to be used with the async context manager
    async_mock_session = AsyncMock()
    async_mock_session.__aenter__.return_value = async_mock_session
    async_mock_session.get = AsyncMock(return_value=async_mock_response)

    with patch("aiohttp.ClientSession", return_value=async_mock_session):
        response = await fetch_data("https://fakeurl.com/api")

    assert response == {"mock_key": "mock_value"}



# ==== TEST: cached_get UTILIZES CACHE ==== #

@pytest.mark.integration
@pytest.mark.asyncio
async def test_cached_get(monkeypatch) -> None:
    """
    Test that cached_get retrieves data from fetch_data only once
    and subsequently returns cached results.
    """
    async_mock_fetch_data = AsyncMock(return_value={"data": 123})
    with patch("app.extract.api_client.fetch_data", async_mock_fetch_data):
        with patch("app.extract.api_client.get_redis") as mock_get_redis:
            # Create a mock Redis instance with no cached data initially.
            redis_instance = AsyncMock()
            redis_instance.get.return_value = None
            mock_get_redis.return_value = redis_instance

            url = "https://fakeurl.com/data"
            result1 = await cached_get("test_key", url)
            result2 = await cached_get("test_key", url)

            # Assert that fetch_data was called only once.
            assert async_mock_fetch_data.call_count == 1
            assert result1 == {"data": 123}
            assert result2 == {"data": 123}



# ==== TEST: parallel_cached_get HANDLES PARALLEL REQUESTS ==== #

@pytest.mark.integration
@pytest.mark.asyncio
async def test_parallel_cached_get() -> None:
    """
    Test that parallel_cached_get processes a list of URLs concurrently,
    invoking cached_get for each URL with a semaphore limit of 5.
    """
    test_urls = [
        "http://fake.com/item/1/",
        "http://fake.com/item/2/",
        "http://fake.com/item/3/",
    ]
    mock_responses = [
        {"id": 1},
        {"id": 2},
        {"id": 3},
    ]
    async_mock_cached = AsyncMock(side_effect=mock_responses)

    with patch("app.extract.api_client.cached_get", async_mock_cached):
        results = await parallel_cached_get("prefix", test_urls)
        assert len(results) == 3
        assert results[0]["id"] == 1
        assert async_mock_cached.call_count == 3
