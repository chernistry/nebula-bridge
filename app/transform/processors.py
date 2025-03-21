from pydantic import BaseModel
from typing import List, Optional

from app.config import WOOKIE_MODE



# ==== DATA MODELS ==== #

class Pilot(BaseModel):
    """
    Represents a pilot with associated details.

    Attributes:
        name (str): The name of the pilot.
        species (Optional[str]): The species of the pilot.
        homeworld (Optional[str]): The homeworld of the pilot.
        films (List[str]): List of films in which the pilot appears.
        edited (str): Timestamp or flag indicating when the record was last edited.
    """
    name: str
    species: Optional[str] = None
    homeworld: Optional[str] = None
    films: List[str] = []
    edited: str

    @classmethod
    def from_api(cls, data: dict) -> "Pilot":
        """
        Transforms API response data into a Pilot model instance.

        Args:
            data (dict): Raw API data for a pilot.

        Returns:
            Pilot: A populated Pilot instance.
        """
        species_val = data.get("species")
        if isinstance(species_val, list):
            species_val = species_val[0] if species_val else None

        return cls(
            name=data.get("name", ""),
            species=species_val,
            homeworld=data.get("homeworld"),
            films=data.get("films", []),
            edited=data.get("edited"),
        )



class VehicleRecord(BaseModel):
    """
    Represents a vehicle record with enriched pilot details.

    Attributes:
        name (str): The name of the vehicle.
        model (str): The model designation of the vehicle.
        vehicle_class (str): The category or class of the vehicle.
        edited (str): Timestamp or flag indicating when the record was last edited.
        pilots (List[Pilot]): A list of associated pilots.
    """
    name: str
    model: str
    vehicle_class: str
    edited: str
    pilots: List[Pilot] = []



# ==== DATA TRANSFORMATION FUNCTION ==== #

def transform_vehicle_data(
        raw_vehicle: dict, pilot_details: List[dict], use_wookiee: bool
) -> VehicleRecord:
    """
    Transforms a raw vehicle record and enriches it with pilot details.

    This function converts raw API data for a vehicle into a structured
    VehicleRecord, including associated pilot information. It applies optional
    Wookiee encoding to selected fields if enabled.

    Args:
        raw_vehicle (dict): Raw vehicle data.
        pilot_details (List[dict]): List of raw pilot data.
        use_wookiee (bool): Flag to apply Wookiee encoding if True.

    Returns:
        VehicleRecord: A structured vehicle record with enriched pilot details.
    """
    pilots = [Pilot.from_api(p) for p in pilot_details]

    vehicle = VehicleRecord(
        name=raw_vehicle.get("name"),
        model=raw_vehicle.get("model"),
        vehicle_class=raw_vehicle.get("vehicle_class"),
        edited=raw_vehicle.get("edited"),
        pilots=pilots,
    )

    # Apply Wookiee encoding if both the configuration and parameter conditions are met.
    if WOOKIE_MODE and use_wookiee:
        from app.transform.wookiee import wookiee_encode  # Import deferred until needed

        vehicle.name = wookiee_encode(vehicle.name)
        vehicle.model = wookiee_encode(vehicle.model)
        vehicle.vehicle_class = wookiee_encode(vehicle.vehicle_class)

        for pilot in vehicle.pilots:
            pilot.name = wookiee_encode(pilot.name)

    return vehicle
