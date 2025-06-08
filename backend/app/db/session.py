from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import SQLAlchemyError

from app.config import settings
from app.db.base import Base

DATABASE_URL = settings.DATABASE_URL

engine = create_engine(
    DATABASE_URL,
    echo=False,
    future=True,       
)

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False, 
    autocommit=False, 
    future=True,       
)


def init_db() -> None:
    """
    Create all tables in the database. Call this at application startup.
    """
    try:
        Base.metadata.create_all(bind=engine)
    except SQLAlchemyError as e:
        raise RuntimeError(f"Could not initialize database tables: {e}") from e


def get_db():
    """
    FastAPI dependency that yields a database session.
    Ensures session is closed after use.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
