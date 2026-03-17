from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Float, Text
from sqlalchemy.sql import func
from database import Base
import datetime

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String) 


class Dataset(Base):
    __tablename__ = "datasets"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(Text, index=True, nullable=False) 
    description = Column(Text)
    author = Column(Text) 
    license = Column(String(255), default="CC-BY-4.0") 
    created_at = Column(DateTime, server_default=func.now())
    owner_id = Column(Integer, ForeignKey("users.id"))

class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    description = Column(String)  
    amount = Column(Float)       
    category = Column(String)    
    transaction_type = Column(String) 
    date = Column(DateTime, server_default=func.now())
            
    owner_id = Column(Integer, ForeignKey("users.id"))