from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class DatasetBase(BaseModel):
    title: str
    description: str
    author: str
    created_at: Optional[str] = None

class DatasetSchema(BaseModel):
    title: str
    description: str
    author: str
    created_at: Optional[str] = None

    class Config:
        from_attributes = True # Pydantic 讀取 SQLAlchemy 物件

class PaginationInfo(BaseModel):
    current_page: int
    total_items: Optional[int] = None
    total_pages: Optional[int] = None

class DatasetResponse(BaseModel):
    status: str
    data: List[DatasetSchema]
    pagination: dict

class UserCreate(BaseModel):
    username: str
    email: str
    password: str

class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    class Config: from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str

class UserSchema(BaseModel):
    id: int
    username: str
    email: str
    class Config:
        from_attributes = True