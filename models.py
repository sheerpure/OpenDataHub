from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from database import Base 
from datetime import datetime

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String) # 確保是這個名稱


class Dataset(Base):
    __tablename__ = "datasets"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(Text, index=True, nullable=False) 
    description = Column(Text)
    author = Column(Text) 
    license = Column(String(255), default="CC-BY-4.0") 
    created_at = Column(DateTime, default=datetime.utcnow)
    owner_id = Column(Integer, ForeignKey("users.id"))