"""
FinTechHub - Identity, Access Management (IAM) & Security Module
Handles password hashing (Bcrypt), JWT token generation, and Field-Level Encryption (AES).
"""

from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from cryptography.fernet import Fernet # [NEW] Added for field-level encryption

import database
import models

# --- Security Configuration ---
# In a production environment, these should be retrieved from environment variables (.env)
SECRET_KEY = "fintechhub-super-secret-key-do-not-share"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # Token validity: 24 hours

# [NEW] Field-Level Encryption Configuration (AES-based Fernet)
# WARNING: If this key is lost, all encrypted data in the database will be unrecoverable.
ENCRYPTION_KEY = Fernet.generate_key() 
cipher_suite = Fernet(ENCRYPTION_KEY)

# Password Hashing context using Bcrypt
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2 scheme for Bearer Token authentication
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

# --- Password Processing Functions ---

def hash_password(password: str) -> str:
    """Transforms a plain-text password into a secure Bcrypt hash."""
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Validates an incoming password against the stored database hash."""
    return pwd_context.verify(plain_password, hashed_password)

# --- [NEW] Field-Level Encryption Functions ---

def encrypt_amount(amount: float) -> str:
    """
    Encrypts a numerical amount into an opaque string before database persistence.
    Protects sensitive financial data against database breaches.
    """
    return cipher_suite.encrypt(str(amount).encode()).decode()

def decrypt_amount(encrypted_str: str) -> float:
    """
    Decrypts an opaque string from the database back into a floating-point number.
    Ensures authorized users can view their actual financial records.
    """
    try:
        decoded_text = cipher_suite.decrypt(encrypted_str.encode()).decode()
        return float(decoded_text)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Security Decryption Failure: Integrity check failed."
        )

# --- JWT Token Processing Functions ---

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Generates a cryptographically signed JWT Access Token for stateless authentication."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    # Inject expiration timestamp into the payload
    to_encode.update({"exp": expire})
    # Sign the token using the SECRET_KEY and HS256 algorithm
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

# --- Authentication Dependencies ---

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(database.get_db)):
    """
    FastAPI Dependency: Validates the JWT token and retrieves the authenticated user.
    Protects private endpoints from unauthorized access.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        # Decode and verify the JWT signature
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    # Cross-reference with the database to ensure the user still exists
    user = db.query(models.User).filter(models.User.username == username).first()
    if user is None:
        raise credentials_exception
    return user