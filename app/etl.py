import os
import json
import asyncio
import logging
import datetime

from app.extract.api_client import cached_get
from app.transform.processors import transform_vehicle_data
from app.load.database import create_db_and_tables, get_session
from app.load.queries import save_vehicle
from app.config import get_base_url, API_TOKEN, USE_PROD

logging.basicConfig(level=logging.INFO)



# ==== PERSISTENCE UTILITY ==== #
# Save the complete API response to a local JSON file as a backup.

def persist_response_to_json(data: dict, prefix: str) -> None:
    """
    Saves the entire API response to a local JSON file as a backup.

    Args:
        data (dict): The JSON data received from the API.
        prefix (str): A prefix for the filename (e.g., 'vehicles_data').
    """
    os.makedirs("backups", exist_ok=True)
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{prefix}_{timestamp}.json"
    filepath = os.path.join("backups", filename)

    try:
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        logging.info(f"Backup saved to {filepath}")
    except Exception as e:
        logging.warning(f"Failed to persist backup JSON: {e}")




# ==== VEHICLE DATA EXTRACTION ==== #
# Retrieve vehicle data and associated film details from the API.

async def get_phantom_menace_film_id(base_url: str, headers: dict) -> str:
    """
    Retrieves the film URL for 'The Phantom Menace'. In production mode, the API
    endpoint includes '/api/films', while in development it omits the prefix.
    Returns an empty string if the film is not found.

    Args:
        base_url (str): The base API URL.
        headers (dict): HTTP headers for the request.

    Returns:
        str: The URL for 'The Phantom Menace' film, or an empty string if not found.
    """
    if USE_PROD:
        film_search_url = f"{base_url}/api/films/?search=The Phantom Menace"
    else:
        film_search_url = f"{base_url}/films/?search=The Phantom Menace"

    film_data = await cached_get("film_phantom_menace", film_search_url, headers=headers)
    results = film_data.get("results", [])
    if results:
        film_url = results[0].get("url", "")
        if film_url:
            return film_url

    logging.error("Phantom Menace not found in API response")
    return ""




async def fetch_vehicles_paginated(url: str, headers: dict) -> dict:
    """
    Aggregates all pages of vehicle data from the API until no further pages exist.

    Args:
        url (str): The URL for the initial request.
        headers (dict): HTTP headers for the request.

    Returns:
        dict: A dictionary in the format {"results": [...]}, containing all vehicle data.
    """
    all_results = []
    next_url = url

    while next_url:
        # Use the next_url in the cache key to uniquely identify the page.
        page_data = await cached_get(f"vehicles_data_{next_url}", next_url, headers=headers)
        page_results = page_data.get("results", [])
        all_results.extend(page_results)

        next_url = page_data.get("next")

    return {"results": all_results}




# ==== ETL PROCESSING ==== #
# Extract, transform, and load vehicle data, optionally filtering by film in production.

async def run_etl(use_wookiee: bool = False, use_prod: bool = False) -> list:
    """
    Extracts and saves vehicle data. In production mode, the data is filtered
    to include only vehicles associated with 'The Phantom Menace'. In development,
    no filtering is applied. Also saves a local JSON backup of the API response.

    Args:
        use_wookiee (bool): Flag to apply Wookiee encoding.
        use_prod (bool): Flag to use production configuration.

    Returns:
        list: A list of saved vehicle objects.
    """
    try:
        create_db_and_tables()
        base_url = get_base_url(force_prod=use_prod)
        headers = {"API-TOKEN": API_TOKEN} if use_prod else {}

        vehicles_url = f"{base_url}/api/vehicles" if use_prod else f"{base_url}/vehicles"
        logging.info(f"Starting ETL from {vehicles_url}")

        # Extract paginated vehicle data.
        paginated_data = await fetch_vehicles_paginated(vehicles_url, headers)
        persist_response_to_json(paginated_data, "vehicles_data")

        raw_vehicles = paginated_data.get("results", [])

        if use_prod:
            phantom_film_url = await get_phantom_menace_film_id(base_url, headers)
            logging.info(f"Phantom Menace URL: {phantom_film_url}")

            if raw_vehicles:
                logging.info(f"First vehicle films: {raw_vehicles[0].get('films', [])}")
            else:
                logging.info("No vehicles found in API response.")

            if phantom_film_url:
                logging.info(f"Total vehicles before filtering: {len(raw_vehicles)}")
                filtered_vehicles = [
                    v
                    for v in raw_vehicles
                    if any(
                        phantom_film_url.rstrip("/") == f.rstrip("/")
                        for f in v.get("films", [])
                    )
                ]
                logging.info(f"Total vehicles after filtering: {len(filtered_vehicles)}")
                raw_vehicles = filtered_vehicles
            else:
                logging.warning("Phantom Menace film URL not found; no filtering applied.")
        else:
            logging.info("Dev environment: skipping film filter.")

        session = get_session()
        stored_vehicles = []

        for vehicle in raw_vehicles:
            pilot_urls = vehicle.get("pilots", [])
            if pilot_urls:
                pilot_ids = [url.split("/")[-2] for url in pilot_urls]
                try:
                    batch_pilots = await cached_get(
                        "pilots_batch",
                        f"{base_url}/api/people/?id={','.join(pilot_ids)}",
                        headers=headers,
                    )
                    pilot_details = batch_pilots.get("results", [])
                except Exception as e:
                    logging.error(f"Batch pilot request failed: {e}")
                    pilot_details = []
            else:
                pilot_details = []

            vehicle.setdefault("model", "N/A")
            vehicle.setdefault("vehicle_class", "N/A")
            vehicle.setdefault("edited", "N/A")

            transformed = transform_vehicle_data(vehicle, pilot_details, use_wookiee=use_wookiee)
            save_vehicle(session, transformed.dict())
            stored_vehicles.append(transformed)

        session.commit()
        return stored_vehicles

    except Exception as e:
        logging.error(f"ETL failed: {str(e)}")
        raise




# ==== MAIN EXECUTION BLOCK ==== #
# Execute the ETL process when this script is run as the main module.

if __name__ == "__main__":
    asyncio.run(run_etl(use_wookiee=False, use_prod=True))
