"""
Database configuration and session management.
"""

import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import settings

# Database URL from environment or settings
DATABASE_URL = os.getenv("DATABASE_URL", settings.DATABASE_URL)

# Create SQLAlchemy engine
if DATABASE_URL.startswith("sqlite"):
    # SQLite configuration for development/testing
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=settings.DEBUG if hasattr(settings, 'DEBUG') else False
    )
else:
    # PostgreSQL configuration for production
    engine = create_engine(
        DATABASE_URL,
        pool_pre_ping=True,
        pool_recycle=300,
        echo=settings.DEBUG if hasattr(settings, 'DEBUG') else False
    )

# Create SessionLocal class
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create Base class for models
Base = declarative_base()

def get_db():
    """
    Dependency to get database session.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    """
    Initialize database tables.
    """
    # Import all models to ensure they are registered with Base
    from app.database import models
    
    # Create all tables
    Base.metadata.create_all(bind=engine)
