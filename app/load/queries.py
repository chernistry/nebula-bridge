from app.load.models import VehicleModel
from sqlmodel import Session



def save_vehicle(session: Session, vehicle_data: dict) -> VehicleModel:
    """
    Saves a vehicle record to the database.

    Args:
        session (Session): An active SQLModel session.
        vehicle_data (dict): A dictionary containing vehicle attributes.

    Returns:
        VehicleModel: The saved vehicle record with updated attributes.
    """
    vehicle = VehicleModel(**vehicle_data)
    session.add(vehicle)
    session.commit()
    session.refresh(vehicle)
    return vehicle
