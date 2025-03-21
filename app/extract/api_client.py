import aiohttp
import asyncio
import json
import time
import logging
from typing import Dict, Any, List, Optional

import redis.asyncio as aioredis
from aiostream import stream

from app.config import REDIS_URL, API_TOKEN


# ==== GLOBALS AND CONFIGURATION ==== #

# In-process cache to reduce redundant Redis and HTTP calls.
_INPROC_CACHE: Dict[str, Any] = {}

# Semaphore to limit concurrent HTTP requests.
SEMAPHORE: asyncio.Semaphore = asyncio.Semaphore(5)



# ==== REDIS CONNECTION MANAGEMENT ==== #

async def get_redis() -> aioredis.Redis:
    """
    Establishes a connection to the Redis server using the configured URL.

    Returns:
        aioredis.Redis: An asynchronous Redis client.

    Raises:
        ConnectionError: If the connection to Redis fails.
    """
    try:
        return await aioredis.from_url(
            REDIS_URL, encoding="utf-8", decode_responses=True
        )
    except Exception as e:
        logging.error("Redis connection failed: %s. Verify Redis configuration.", e)
        raise ConnectionError("Could not connect to Redis") from e



# ==== DATA FETCHING FROM HTTP ENDPOINTS ==== #

async def fetch_data(
        url: str,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
) -> Any:
    """
    Fetches JSON data from the given URL using an asynchronous HTTP GET request.

    Args:
        url (str): The URL to send the GET request to.
        params (Optional[Dict[str, Any]]): URL parameters for the request.
        headers (Optional[Dict[str, str]]): Headers to include in the request.

    Returns:
        Any: The JSON response data.

    Raises:
        aiohttp.ClientResponseError: If an HTTP error occurs.
        Exception: For all other errors during the request.
    """
    try:
        async with aiohttp.ClientSession() as session:
            response = await session.get(url, params=params, headers=headers)
            response.raise_for_status()
            return await response.json()
    except aiohttp.ClientResponseError as e:
        logging.error("HTTP error while fetching %s: %s", url, e)
        raise
    except Exception as e:
        logging.error("Error during fetch_data for %s: %s", url, e)
        raise



# ==== CACHING LOGIC FOR HTTP RESPONSES ==== #

async def cached_get(
        cache_key: str,
        url: str,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        ttl: int = 3600,
) -> Any:
    """
    Retrieves data using a cache. It first checks an in-process cache,
    then Redis, and if not found, fetches from the given URL.

    Args:
        cache_key (str): Key to identify the cached data.
        url (str): The URL to fetch data from if not cached.
        params (Optional[Dict[str, Any]]): URL parameters for the request.
        headers (Optional[Dict[str, str]]): Headers for the HTTP request.
        ttl (int): Time-to-live for the cache in seconds.

    Returns:
        Any: The fetched or cached data.
    """
    # Check in-process cache
    if cache_key in _INPROC_CACHE:
        return _INPROC_CACHE[cache_key]

    redis_client = await get_redis()
    cached = await redis_client.get(cache_key)

    if cached:
        try:
            data = json.loads(cached)
            _INPROC_CACHE[cache_key] = data
            return data
        except json.JSONDecodeError:
            logging.warning("Corrupted Redis cache for key %s. Refetching.", cache_key)

    data = await fetch_data(url, params=params, headers=headers)

    try:
        await redis_client.set(cache_key, json.dumps(data), ex=ttl)
    except Exception as e:
        logging.warning("Failed to cache response for key %s: %s", cache_key, e)

    _INPROC_CACHE[cache_key] = data
    return data



# ==== PARALLEL DATA FETCHING WITH CACHING ==== #

async def parallel_cached_get(
        cache_key_prefix: str,
        urls: List[str],
        headers: Optional[Dict[str, str]] = None,
        ttl: int = 3600,
) -> List[Any]:
    """
    Fetches data from multiple URLs in parallel with caching.

    Each URL's cache key is generated using a prefix and the last segment
    of the URL.

    Args:
        cache_key_prefix (str): Prefix for generating cache keys.
        urls (List[str]): A list of URLs to fetch data from.
        headers (Optional[Dict[str, str]]): HTTP headers for the requests.
        ttl (int): Cache time-to-live in seconds.

    Returns:
        List[Any]: A list of responses corresponding to the URLs.
    """
    async def fetch_single(url: str) -> Any:
        async with SEMAPHORE:
            suffix = url.rstrip("/").split("/")[-1]
            cache_key = f"{cache_key_prefix}_{suffix}"
            return await cached_get(cache_key, url, headers=headers, ttl=ttl)

    mapped_stream = stream.map(stream.iterate(urls), fetch_single, ordered=False)
    results = [item async for item in mapped_stream]
    return results



# ==== SPECIALIZED CACHING FOR ODATA RESPONSES ==== #

async def cache_odate_response(user_id: str, response: Any, ttl: int = 3600) -> None:
    """
    Caches an OData response for a specific user.

    Args:
        user_id (str): The user identifier.
        response (Any): The response data to cache.
        ttl (int): Cache time-to-live in seconds.
    """
    redis_client = await get_redis()
    cache_data = {"timestamp": time.time(), "response": response}

    try:
        await redis_client.set(
            f"odata_flight_{user_id}", json.dumps(cache_data), ex=ttl
        )
    except Exception as e:
        logging.warning("Failed to cache OData response for user_id %s: %s", user_id, e)



async def get_odate_response(user_id: str, ttl: int = 3600) -> Optional[Any]:
    """
    Retrieves a cached OData response for a specific user if valid.

    Args:
        user_id (str): The user identifier.
        ttl (int): Time-to-live in seconds for cache validity.

    Returns:
        Optional[Any]: The cached response if valid; otherwise, None.
    """
    redis_client = await get_redis()
    cached = await redis_client.get(f"odata_flight_{user_id}")

    if cached:
        try:
            cache_data = json.loads(cached)
            cached_time = cache_data.get("timestamp")

            if cached_time and (time.time() - cached_time > ttl):
                logging.info("Cache expired for user_id %s; refetch needed.", user_id)
                return None

            return cache_data.get("response")
        except json.JSONDecodeError:
            logging.warning("Corrupted OData cache for user_id %s; refetch needed.", user_id)
            return None

    return None
