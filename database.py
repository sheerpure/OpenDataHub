from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from config import settings

# 建立連線引擎
engine = create_engine(settings.DATABASE_URL)

# 建立 SessionLocal 
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

# FastAPI Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()