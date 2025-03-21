from typing import Optional
from sqlmodel import SQLModel, Field



# ==== VEHICLE MODEL DEFINITION ==== #

class VehicleModel(SQLModel, table=True):
    """
    Represents a vehicle record in the database.

    Attributes:
        id (Optional[int]): The primary key of the vehicle record.
        name (str): The name of the vehicle.
        model (str): The model designation of the vehicle.
        vehicle_class (str): The class or category of the vehicle.
        edited (str): A flag or timestamp indicating if the record was edited.
    """
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    model: str
    vehicle_class: str
    edited: str
