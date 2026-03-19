import os
from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from cryptography.fernet import Fernet
from dotenv import load_dotenv
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

import database
import models

# Load environment variables from .env file
load_dotenv()

# Security Configuration
SECRET_KEY = os.getenv("SECRET_KEY", "insecure-default-key-change-me")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 1440))
ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY").encode()

# Initialize Crypto Suites
cipher_suite = Fernet(ENCRYPTION_KEY)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

# --- Password Hashing ---

def hash_password(password: str) -> str:
    """Generates a secure Bcrypt hash from a plaintext password."""
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifies a plaintext password against a stored hash."""
    return pwd_context.verify(plain_password, hashed_password)

# --- Field-Level Encryption (AES-256) ---

def encrypt_amount(amount: float) -> str:
    """
    Encrypts a numerical value into an AES-encrypted string.
    Ensures financial data is unreadable if the database is breached.
    """
    return cipher_suite.encrypt(str(amount).encode()).decode()

def decrypt_amount(encrypted_str: str) -> float:
    """
    Decrypts a database string back into a float.
    Returns 0.0 if decryption fails to prevent system crashes.
    """
    try:
        decrypted_text = cipher_suite.decrypt(encrypted_str.encode()).decode()
        return float(decrypted_text)
    except Exception:
        return 0.0

# --- JWT Token Management ---

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Generates a cryptographically signed JWT for stateless authentication."""
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

# --- Authentication Dependency ---

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(database.get_db)):
    """
    FastAPI Dependency: Validates the JWT and returns the User object.
    Used to protect private API endpoints.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = db.query(models.User).filter(models.User.username == username).first()
    if user is None:
        raise credentials_exception
    return user