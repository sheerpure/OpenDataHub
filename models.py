from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from database import Base 
from datetime import datetime

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)


class Dataset(Base):
    __tablename__ = "datasets"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(Text, index=True, nullable=False) 
    description = Column(Text)
    author = Column(Text) 
    license = Column(String(255), default="CC-BY-4.0") 
    created_at = Column(DateTime, default=datetime.utcnow)
    owner_id = Column(Integer, ForeignKey("users.id"))