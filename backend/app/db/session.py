from pathlib import Path
from urllib.parse import urlparse

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import os

load_dotenv(Path(__file__).resolve().parents[2] / ".env")

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./interview.db")

if "username:password" in DATABASE_URL:
    DATABASE_URL = "sqlite:///./interview.db"

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
_initialized = False


def get_db_session():
    init_db()
    return SessionLocal()


def init_db():
    global _initialized
    if _initialized:
        return
    from app.models.interview import Base

    Base.metadata.create_all(bind=engine)
    _initialized = True
