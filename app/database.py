"""
Database Configuration and Session Management
"""

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import scoped_session, sessionmaker

from config import settings

# Create engine
engine = create_engine(
    settings.DATABASE_URL,
    connect_args={'check_same_thread': False} if 'sqlite' in settings.DATABASE_URL else {},
    echo=settings.DEBUG
)

# Create session factory
db_session = scoped_session(
    sessionmaker(autocommit=False, autoflush=False, bind=engine)
)

# Base class for models
Base = declarative_base()
Base.query = db_session.query_property()


def init_db():
    """Initialize database tables"""
    # Import all models to register them with Base
    from app.models import job, file_metadata, analysis

    Base.metadata.create_all(bind=engine)


def shutdown_session(exception=None):
    """Clean up database session"""
    db_session.remove()
