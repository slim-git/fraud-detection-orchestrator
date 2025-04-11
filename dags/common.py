import logging
from airflow.decorators import task
import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from datetime import datetime, timedelta
from typing import Generator

# Load environment variables from .env file
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)

default_args = {
    "owner": "airflow",
    "start_date": datetime.now() - timedelta(minutes=5),
    "catchup": False
}

def get_session() -> Generator:
    """
    Get a connection to the Postgres database
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@task(task_id="check_db_connection")
def check_db_connection():
    """
    Checks the connection to the database.
    """
    try:
        with next(get_session()) as session:
            session.execute(text("SELECT 1"))
            logging.info("Database connection is successful.")
    except Exception as e:
        logging.error(f"Database connection failed: {e}")
        raise