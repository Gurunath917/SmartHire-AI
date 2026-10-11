"""
Database initialization script.
Run this once to create all tables:
    python -m app.database.init_db
"""
from loguru import logger
from app.database.connection import engine, Base

# Import all models so Base.metadata knows about every table
import app.models  # noqa: F401


def init_db() -> None:
    """Create all tables if they don't exist."""
    logger.info("Creating database tables...")
    try:
        Base.metadata.create_all(bind=engine)
        logger.success("All database tables created successfully.")
    except Exception as e:
        logger.error("Failed to create tables: {}", e)
        raise


def drop_all_tables() -> None:
    """
    Drop all tables — USE WITH CAUTION.
    Only call this explicitly in dev/test; never in production flow.
    """
    logger.warning("Dropping ALL database tables...")
    Base.metadata.drop_all(bind=engine)
    logger.warning("All tables dropped.")


if __name__ == "__main__":
    init_db()
