"""
OpenDataHub - 身份驗證與授權模組
處理密碼雜湊 (Hashing)、Token 簽發與驗證。
使用 Bcrypt 加密與 JWT (JSON Web Token) 實作無狀態驗證。
"""

from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
import database, models

# --- 安全配置 ---
# SECRET_KEY 從環境變數 (.env) 讀取
SECRET_KEY = "opendatahub-super-secret-key-change-me-in-production"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # Token 有效期設為 24 小時

# 設定密碼雜湊演算法
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# 設定 OAuth2 認證流程的 URL 進入點
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

# --- 密碼處理函數 ---

def hash_password(password: str) -> str:
    """將明文密碼轉為 Bcrypt 雜湊值"""
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """驗證輸入的密碼是否與資料庫中的雜湊值匹配"""
    return pwd_context.verify(plain_password, hashed_password)

# --- JWT Token 處理函數 ---

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """產生加密的 JWT Access Token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    # 將到期時間加入 Payload
    to_encode.update({"exp": expire})
    # 使用 SECRET_KEY 與 HS256 演算法簽署 Token
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

# --- 權限驗證依賴項 (Dependency) ---

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(database.get_db)):
    """
    這是一個 FastAPI 依賴項。
    任何受保護的 API 只要加上這個依賴，就能確保只有登入者可以存取。
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="無法驗證憑證",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        # 解碼 JWT Token
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    # 資料庫確認使用者是否存在
    user = db.query(models.User).filter(models.User.username == username).first()
    if user is None:
        raise credentials_exception
    return user