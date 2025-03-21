#!/usr/bin/env python3
import asyncio
import logging
import json
import os
import urllib.parse
from typing import Optional, List, Dict, Any

import requests
import redis
from fastapi import FastAPI, Query, HTTPException
from fastapi.responses import JSONResponse

from app.etl import run_etl
from app.extract.api_client import parallel_cached_get
from app.config import DEV_BASE_URL, PROD_BASE_URL, API_TOKEN, USE_PROD
from app.load.database import create_db_and_tables, get_session
from app.load.models import VehicleModel
import app.config as conf


# ==== Logging Configuration ==== #
logging.basicConfig(level=logging.INFO)


# ==== FastAPI Application Initialization ==== #
# Initialize FastAPI with a root path for proper proxy support.
app = FastAPI(root_path="/api")


# ==== Redis Client Setup ==== #
redis_url: str = os.getenv("REDIS_URL", "redis://127.0.0.1:6379")
parsed = urllib.parse.urlparse(redis_url)
_redis_client = redis.Redis(host=parsed.hostname, port=parsed.port, decode_responses=True)

# Default cache time-to-live in seconds (if needed elsewhere)
CACHE_TTL: int = 3600





# ==== TEAM SALARY CALCULATION FUNCTION ==== #
def calculate_team_salaries(
        employees: List[Dict[str, Any]]
) -> Dict[int, float]:
    """
    Calculates the total team salary for each top-level manager.

    Args:
        employees (List[Dict[str, Any]]): A list of employee dictionaries,
            each containing 'id', 'manager_id', and 'salary'.

    Returns:
        Dict[int, float]: A mapping from employee ID (for top-level managers)
            to the total salary of their team.
    """
    subordinates: Dict[Optional[int], List[int]] = {}
    for emp in employees:
        mgr = emp.get("manager_id")
        if mgr is not None:
            subordinates.setdefault(mgr, []).append(emp["id"])

    salary_map: Dict[int, float] = {emp["id"]: emp["salary"] for emp in employees}

    def total_salary(emp_id: int) -> float:
        total = salary_map.get(emp_id, 0)
        for sub_id in subordinates.get(emp_id, []):
            total += total_salary(sub_id)
        return total

    return {emp["id"]: total_salary(emp["id"])
            for emp in employees if emp.get("manager_id") is None}





# ==== Application Startup Event ==== #
@app.on_event("startup")
async def startup_event() -> None:
    """
    Initializes the database and logs the environment configuration
    during application startup.
    """
    create_db_and_tables()
    if not USE_PROD:
        logging.warning("USE_PROD is disabled. All API calls will use the DEV environment.")





# ==== ETL Endpoint ==== #
@app.get("/run-etl")
async def run_etl_endpoint(use_wookiee: bool = Query(False)) -> Dict[str, Any]:
    """
    Runs the ETL process and returns the loaded vehicles.

    Args:
        use_wookiee (bool): Flag to alter ETL behavior. Defaults to False.

    Returns:
        Dict[str, Any]: A dictionary with a message and list of vehicle data.
    """
    try:
        vehicles = await run_etl(use_wookiee=use_wookiee, use_prod=USE_PROD)
        return {
            "message": f"ETL process completed. Loaded {len(vehicles)} vehicles.",
            "vehicles": [v.dict() for v in vehicles],
        }
    except Exception as e:
        logging.error("Error in /run-etl endpoint: %s", e)
        raise HTTPException(status_code=500, detail=str(e))





# ==== Vehicle Extraction Endpoint ==== #
@app.get("/extract-vehicles-phantom")
async def extract_vehicles_phantom() -> Dict[str, Any]:
    """
    Extracts vehicles from the database.

    Returns:
        Dict[str, Any]: A dictionary containing a list of vehicles.
    """
    session = get_session()
    vehicles = session.query(VehicleModel).all()
    session.close()
    return {"vehicles": [v.dict() for v in vehicles]}





# ==== Character Search Endpoint ==== #
@app.get("/search-characters-prod")
async def search_characters_prod(query: str = "Grievous") -> Dict[str, Any]:
    """
    Searches for characters using the production API.

    Args:
        query (str): The search query. Defaults to "Grievous".

    Returns:
        Dict[str, Any]: A JSON response containing valid characters or a message.
    """
    if not conf.USE_PROD:
        raise HTTPException(403, "Enable USE_PROD in .env")
    base_url = conf.PROD_BASE_URL
    headers = {"API-TOKEN": conf.API_TOKEN}

    try:
        response = requests.get(
            f"{base_url}/api/people/?search={query}&expand=species,films",
            headers=headers,
        )
        response.raise_for_status()
        characters = response.json().get("results", [])

        # Collect URLs for species and films
        species_urls = {url for char in characters for url in char.get("species", []) if url}
        film_urls = {url for char in characters for url in char.get("films", []) if url}

        try:
            species_data = await parallel_cached_get("species", list(species_urls), headers=headers)
        except Exception as e:
            logging.error("Species batch request failed; skipping invalid URLs: %s", e)
            species_data = []

        try:
            film_data = await parallel_cached_get("films", list(film_urls), headers=headers)
        except Exception as e:
            logging.error("Film batch request failed; skipping invalid URLs: %s", e)
            film_data = []

        species_map = {s.get("url"): s.get("name", "") for s in species_data}
        film_map = {f.get("url"): f.get("title", "") for f in film_data}

        valid_chars = []
        for char in characters:
            char_species_urls = [u for u in char.get("species", []) if u]
            char_film_urls = [u for u in char.get("films", []) if u]
            species_names = [species_map.get(su, "") for su in char_species_urls]
            film_titles = [film_map.get(fu, "") for fu in char_film_urls]
            if "Droid" in species_names:
                continue
            if len(film_titles) >= 2:
                valid_chars.append({
                    "name": char["name"],
                    "species": species_names,
                    "edited": char.get("edited"),
                    "film_count": len(film_titles),
                })

        if valid_chars:
            return JSONResponse(content={"characters": valid_chars})
        else:
            return JSONResponse(content={"message": "No valid characters found"})
    except requests.exceptions.RequestException as e:
        logging.error("Character search failed: %s", str(e))
        raise HTTPException(500, "Error fetching characters from API")





# ==== Team Salary Calculation Endpoint ==== #
@app.get("/calculate-team-salary")
async def calculate_team_salary() -> Dict[str, Any]:
    """
    Calculates the total team salary for each employee by fetching employee data
    from the production API.

    Returns:
        Dict[str, Any]: A dictionary containing team salary information.
    """
    try:
        emp_response = requests.get(
            f"{PROD_BASE_URL}/api/get_employees", headers={"API-TOKEN": API_TOKEN}
        )
        emp_response.raise_for_status()
        employees = emp_response.json().get("employees", [])
        if not isinstance(employees, list):
            logging.error("Unexpected API response format: %s", employees)
            raise HTTPException(500, "Invalid API response format")
        required_fields = {"EmployeeID", "ManagerID", "Salary"}
        if not employees or not required_fields.issubset(employees[0].keys()):
            raise HTTPException(
                500, f"Missing required fields: {list(required_fields)}"
            )
        formatted_employees = []
        for emp in employees:
            emp_id = int(emp["EmployeeID"])
            manager_val = emp["ManagerID"]
            manager_id = int(manager_val) if manager_val not in (None, "", "null") else None
            salary = float(emp["Salary"])
            formatted_employees.append({
                "id": emp_id,
                "manager_id": manager_id,
                "salary": salary,
            })

        salary_map = {e["id"]: e["salary"] for e in formatted_employees}
        subordinates = {e["id"]: [] for e in formatted_employees}
        for e in formatted_employees:
            if e["manager_id"] in subordinates:
                subordinates[e["manager_id"]].append(e["id"])

        def compute_salary(emp_id: int) -> float:
            return salary_map[emp_id] + sum(
                compute_salary(sub) for sub in subordinates.get(emp_id, [])
            )

        team_salaries = {e["id"]: compute_salary(e["id"]) for e in formatted_employees}
        results = [{"id": emp_id, "TotalTeamSalary": total} for emp_id, total in team_salaries.items()]
        return {"team_salaries": results}
    except Exception as e:
        logging.error("Salary calculation failed: %s", str(e))
        raise HTTPException(500, str(e))





# ==== Mock Data and People Data Retrieval ==== #
def _fetch_mock_data() -> List[Dict[str, Any]]:
    """
    Provides a mock dataset of people with flight information.

    Returns:
        List[Dict[str, Any]]: A list of dictionaries representing mock people data.
    """
    return [
        {
            "FirstName": "John",
            "LastName": "Doe",
            "Flights": [
                {"AirlineCode": "AA", "Distance": 1500},
                {"AirlineCode": "UA", "Distance": 2000},
            ],
        },
        {
            "FirstName": "Jane",
            "LastName": "Smith",
            "Flights": [
                {"AirlineCode": "DL", "Distance": 2200},
                {"AirlineCode": "AA", "Distance": 2100},
            ],
        },
        {
            "FirstName": "SingleAirline",
            "LastName": "Person",
            "Flights": [{"AirlineCode": "SW", "Distance": 1200}],
        },
    ]



def fetch_people_data_from_tripin() -> List[Dict[str, Any]]:
    """
    Fetches people data from the TripPin service using OData.

    Returns:
        List[Dict[str, Any]]: A list of people with flight information.
    """
    base_url = "https://services.odata.org/V4/TripPinServiceRW"
    people_url = (
        f"{base_url}/People?$select=FirstName,LastName,UserName"
        f"&$expand=Flights($select=Distance,AirlineCode)"
    )
    all_people: List[Dict[str, Any]] = []
    next_link: Optional[str] = people_url
    while next_link:
        logging.info("Fetching: %s", next_link)
        resp = requests.get(next_link, headers={"User-Agent": "Mozilla/5.0"})
        resp.raise_for_status()
        data = resp.json()
        value = data.get("value", [])
        all_people.extend(value)
        next_link = data.get("@odata.nextLink")
    return all_people



def get_cached_people_data(cache_key: str) -> Optional[List[Dict[str, Any]]]:
    """
    Retrieves cached people data from Redis.

    Args:
        cache_key (str): The key to use for retrieving data.

    Returns:
        Optional[List[Dict[str, Any]]]: Cached people data if available, else None.
    """
    cached_data = _redis_client.get(cache_key)
    if not cached_data:
        return None
    try:
        return json.loads(cached_data)
    except json.JSONDecodeError:
        logging.warning("Corrupted Redis cache for key=%s. Ignoring.", cache_key)
        return None



def store_people_data_in_cache(cache_key: str, people_data: List[Dict[str, Any]]) -> None:
    """
    Stores people data in Redis cache with an expiration time.

    Args:
        cache_key (str): The key under which data is stored.
        people_data (List[Dict[str, Any]]): The data to be cached.
    """
    try:
        _redis_client.setex(cache_key, CACHE_TTL, json.dumps(people_data))
        logging.info("Stored updated data in Redis cache (key=%s).", cache_key)
    except Exception as e:
        logging.warning("Failed to store data in Redis: %s", e)





# ==== OData Longest Flight Endpoint ==== #
@app.get("/odata-longest-flight")
def odata_longest_flight(use_mock: bool = Query(False)) -> Dict[str, Any]:
    """
    Retrieves the longest flight details from people data, either from
    a real fetch or mock data, and caches the result in Redis.

    Args:
        use_mock (bool): Whether to use mock data. Defaults to False.

    Returns:
        Dict[str, Any]: A dictionary containing person details with the longest flight.
    """
    cache_key = "trip_pin_people_mock" if use_mock else "trip_pin_people_real"
    people_data = get_cached_people_data(cache_key)
    fetched_from_service = False

    if not people_data:
        logging.info("No valid cache for key=%s. Attempting fresh fetch...", cache_key)
        try:
            if use_mock:
                logging.info("[Mock] Using local mock dataset.")
                people_data = _fetch_mock_data()
            else:
                logging.info("[TripPin] Attempting real ephemeral data fetch.")
                people_data = fetch_people_data_from_tripin()
            store_people_data_in_cache(cache_key, people_data)
            fetched_from_service = True
        except requests.RequestException as ex:
            logging.error("Real fetch from TripPin failed: %s", ex)
            people_data = get_cached_people_data(cache_key)
            if not people_data:
                raise HTTPException(status_code=502, detail="Failed real fetch, no cache fallback.")

    if not people_data:
        return {"message": "No data available (cache or new)."}

    best_distance = -1.0
    best_person: Optional[Dict[str, Any]] = None
    for person in people_data:
        flights = person.get("Flights", [])
        if not flights:
            continue
        airline_codes = {f.get("AirlineCode") for f in flights if f.get("AirlineCode")}
        if len(airline_codes) < 2:
            continue
        max_dist = max(float(f.get("Distance", 0)) for f in flights if f.get("Distance"))
        if max_dist > best_distance:
            best_distance = max_dist
            best_person = {
                "FirstName": person.get("FirstName", ""),
                "LastName": person.get("LastName", ""),
                "Airlines": sorted(airline_codes),
            }

    if not best_person:
        return {"message": "No valid flights"}

    if fetched_from_service:
        logging.info("[LongestFlight] Returned fresh fetch data. (use_mock=%s)", use_mock)
    else:
        logging.info("[LongestFlight] Returned data from Redis cache. (use_mock=%s)", use_mock)

    full_name = f"{best_person.get('FirstName', '')} {best_person.get('LastName', '')}".strip()
    return {
        "person": full_name,
        "distance": best_distance,
        "airlines": best_person["Airlines"],
    }





# ==== Postman Collection Generation Endpoint ==== #
@app.get("/generate-postman")
def generate_postman() -> Dict[str, Any]:
    """
    Generates a Postman collection JSON for API testing and writes it to a file.

    Returns:
        Dict[str, Any]: The generated Postman collection.
    """
    collection = {
        "info": {
            "name": "Taboola Integration Test Collection",
            "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json",
        },
        "item": [
            {
                "name": "Extract Vehicles (Phantom Menace, PROD)",
                "request": {
                    "method": "GET",
                    "header": [{"key": "API-TOKEN", "value": API_TOKEN}],
                    "url": {
                        "raw": f"{{{{PROD_BASE_URL}}}}/api/vehicles?filter_film_title=The Phantom Menace",
                        "host": ["{{PROD_BASE_URL}}"],
                        "path": ["api", "vehicles"],
                        "query": [{"key": "filter_film_title", "value": "The Phantom Menace"}],
                    },
                },
            },
            {
                "name": "Search Characters (PROD)",
                "request": {
                    "method": "GET",
                    "header": [{"key": "API-TOKEN", "value": API_TOKEN}],
                    "url": {
                        "raw": f"{{{{PROD_BASE_URL}}}}/api/people/?search=Grievous",
                        "host": ["{{PROD_BASE_URL}}"],
                        "path": ["api", "people"],
                        "query": [{"key": "search", "value": "Grievous"}],
                    },
                },
            },
            {
                "name": "Calculate Team Salary (SQL)",
                "request": {
                    "method": "GET",
                    "url": {
                        "raw": "http://localhost:8000/calculate-team-salary",
                        "host": ["localhost"],
                        "port": "8000",
                        "path": ["calculate-team-salary"],
                    },
                },
            },
            {
                "name": "OData Longest Flight (Mock vs Real)",
                "request": {
                    "method": "GET",
                    "url": {
                        "raw": "http://localhost:8000/odata-longest-flight?use_mock=false",
                        "host": ["localhost"],
                        "port": "8000",
                        "path": ["odata-longest-flight"],
                        "query": [{"key": "use_mock", "value": "false"}],
                    },
                },
            },
        ],
    }
    with open("Taboola_Task.postman_collection.json", "w") as f:
        json.dump(collection, f, indent=4)
    return collection



# ==== Application Entry Point ==== #
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)