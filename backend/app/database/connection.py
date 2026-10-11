"""
Database connection — SQLAlchemy engine, session factory, and Base.
All ORM models import Base from here.
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from sqlalchemy.pool import NullPool

from app.config import settings


class Base(DeclarativeBase):
    """Shared declarative base for all ORM models."""
    pass


# ── Engine ───────────────────────────────────────────────────────────────────
# NullPool is used to avoid connection pool issues in dev/test.
# Switch to QueuePool or connection pool settings for production.
engine = create_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,          # logs SQL when DEBUG=True
    pool_pre_ping=True,           # verify connection before use
)

# ── Session factory ──────────────────────────────────────────────────────────
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)


# ── Dependency — use this in FastAPI route handlers ──────────────────────────
def get_db():
    """
    Yields a database session and ensures it is closed after each request.
    Usage:
        @router.get("/")
        def my_route(db: Session = Depends(get_db)):
            ...
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
