from sqlalchemy import create_engine, event
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.engine import Engine

# Database URL for SQLite
SQLALCHEMY_DATABASE_URL = "sqlite:///./fintech_ledger.db"

# Create the SQLAlchemy engine
# 'check_same_thread': False is required specifically for SQLite + FastAPI
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)

# --- CRITICAL: SQLite Foreign Key Enabler ---
# This listener ensures that 'ON DELETE CASCADE' is respected by SQLite.
# Without this, deleting an account will NOT delete its transactions.
@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()

# Create SessionLocal class for database operations
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for DB models
Base = declarative_base()

# Dependency to get DB session in FastAPI routes
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()