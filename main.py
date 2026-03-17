# from fastapi import FastAPI

# app = FastAPI(title="OpenDataHub - Mini Depositar")

# @app.get("/")
# def read_root():
#     return {"message": "Hello from OpenDataHub! 🚀 這是我的研究資料平台 demo"}

# @app.get("/docs")
# def docs():
#     return {"redirect": "去 http://127.0.0.1:8000/docs 看自動 API 文件"}

# @app.get("/hello/{name}")
# def say_hello(name: str):
#     return {"message": f"嗨，{name}！歡迎來到 OpenDataHub 🎉"}

from fastapi import FastAPI, Depends, Query, Request, HTTPException, status
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from sqlalchemy import or_
from fastapi.security import OAuth2PasswordRequestForm
import math
import os
from pathlib import Path

# Internal module imports
from database import get_db
import models
import schemas
import auth
from search import full_text_search, index_dataset
from auth import get_current_user

# --- Path Configuration ---
BASE_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

# --- App Initialization ---
app = FastAPI(
    title="OpenDataHub FinTech",
    description="Enterprise-grade financial analytics and data repository.",
    version="0.5.0",
    docs_url="/api/v1/docs", # Custom docs path
    redoc_url=None
)

# Database Synchronization
@app.on_event("startup")
def configure_db():
    models.Base.metadata.create_all(bind=get_db().__next__().get_bind())

# --- Frontend Shell (SSR) ---

@app.get("/", response_class=HTMLResponse, tags=["Frontend"])
async def home(request: Request):
    """Serves the main SPA Dashboard."""
    return templates.TemplateResponse("index.html", {"request": request})

# --- Identity & Access Management (IAM) ---

@app.post("/api/v1/auth/register", response_model=schemas.UserSchema, tags=["Auth"])
def register(user_in: schemas.UserCreate, db: Session = Depends(get_db)):
    """User Registration with password hashing."""
    db_user = db.query(models.User).filter(
        or_(models.User.username == user_in.username, models.User.email == user_in.email)
    ).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Identity already exists.")
    
    new_user = models.User(
        username=user_in.username,
        email=user_in.email,
        hashed_password=auth.hash_password(user_in.password)
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

@app.post("/api/v1/auth/login", tags=["Auth"])
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """Authenticates user and issues a JWT Bearer Token."""
    user = db.query(models.User).filter(models.User.username == form_data.username).first()
    if not user or not auth.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials.")
    
    access_token = auth.create_access_token(data={"sub": user.username})
    return {"access_token": access_token, "token_type": "bearer"}

# --- Financial Transaction Engine ---

@app.get("/api/v1/transactions", tags=["Finance"])
def list_transactions(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    """Retrieves all transaction records for the authenticated user."""
    return db.query(models.Transaction).filter(
        models.Transaction.owner_id == current_user.id
    ).order_by(models.Transaction.id.desc()).all()

@app.post("/api/v1/transactions", tags=["Finance"], status_code=201)
def create_transaction(
    tx_in: schemas.TransactionCreate, 
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    """Persists a new financial record to the ledger."""
    new_tx = models.Transaction(**tx_in.dict(), owner_id=current_user.id)
    db.add(new_tx)
    db.commit()
    db.refresh(new_tx)
    return new_tx

@app.delete("/api/v1/transactions/{tx_id}", tags=["Finance"])
def delete_transaction(
    tx_id: int, 
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    """Removes a specific transaction after verifying ownership."""
    tx = db.query(models.Transaction).filter(
        models.Transaction.id == tx_id, 
        models.Transaction.owner_id == current_user.id
    ).first()
    if not tx:
        raise HTTPException(status_code=404, detail="Transaction not found.")
    db.delete(tx)
    db.commit()
    return {"status": "deleted"}

@app.get("/api/v1/dashboard", tags=["Finance"])
def get_dashboard_summary(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    """Aggregates financial KPIs for dashboard visualization."""
    txs = db.query(models.Transaction).filter(models.Transaction.owner_id == current_user.id).all()
    income = sum(t.amount for t in txs if t.transaction_type == "income")
    expense = sum(t.amount for t in txs if t.transaction_type == "expense")
    return {"total_income": income, "total_expense": expense, "balance": income - expense}

