import logging
from airflow.decorators import task
import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from datetime import datetime, timedelta
from typing import Generator
from contextlib import contextmanager

# Load environment variables from .env file
load_dotenv()

_engine = None
_SessionLocal = None

default_args = {
    "owner": "airflow",
    "start_date": datetime.now() - timedelta(minutes=5),
    "catchup": False
}

def get_engine():
    global _engine
    
    if _engine is None:
        # Load the database URL from environment variables
        database_url = os.getenv("DATABASE_URL")
        if not database_url:
            raise ValueError("DATABASE_URL is not set in environment variables")
        
        # Create the SQLAlchemy engine
        _engine = create_engine(database_url, pool_pre_ping=True)
    
    return _engine

def get_session_local() -> sessionmaker:
    global _SessionLocal

    if _SessionLocal is None:
        # Create a new session local
        _SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=get_engine())
    
    return _SessionLocal

@contextmanager
def get_session() -> Generator[Session, None, None]:
    """
    Get a connection to the Postgres database
    """
    SessionLocal = get_session_local()
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
        with get_session() as session:
            session.execute(text("SELECT 1"))
            logging.info("Database connection is successful.")
    except Exception as e:
        logging.error(f"Database connection failed: {e}")
        raise