from sqlmodel import SQLModel, create_engine, Session
from app.config import DB_PATH  # Use DB_PATH for database connection configuration


# ==== DATABASE CONFIGURATION ==== #

DATABASE_URL = f"sqlite:///{DB_PATH}"  # Construct the SQLite connection URL using DB_PATH
engine = create_engine(
    DATABASE_URL,
    echo=True,
    connect_args={"check_same_thread": False},
)



# ==== DATABASE INITIALIZATION ==== #

def create_db_and_tables() -> None:
    """
    Creates the database and all defined tables based on the SQLModel metadata.

    This function imports the necessary models from the app.load module and
    initializes the database schema.
    """
    from app.load import models  # Import models to ensure they are registered with SQLModel
    SQLModel.metadata.create_all(engine)



# ==== SESSION MANAGEMENT ==== #

def get_session() -> Session:
    """
    Creates and returns a new database session.

    Returns:
        Session: A new SQLModel database session instance.
    """
    return Session(engine)
