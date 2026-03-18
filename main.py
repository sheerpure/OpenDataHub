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

from fastapi import FastAPI, Depends, Request, HTTPException, status
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from sqlalchemy import or_
from fastapi.security import OAuth2PasswordRequestForm
from pathlib import Path

# Internal module imports
from database import get_db
import models
import schemas
import auth
from auth import get_current_user

# --- Path Configuration ---
BASE_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

# --- App Initialization ---
app = FastAPI(
    title="FinTechHub Secure",
    description="Enterprise-grade financial ledger with field-level encryption and audit logging.",
    version="1.0.0",
    docs_url="/api/v1/docs",
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

# --- Internal Audit Utility ---

def create_audit_log(db: Session, user_id: int, action: str, target_id: int, details: str):
    """Captures a permanent record of user actions for compliance and security auditing."""
    new_log = models.AuditLog(
        user_id=user_id,
        action=action,
        target_id=target_id,
        details=details
    )
    db.add(new_log)

# --- Account Management Engine ---

@app.get("/api/v1/accounts", tags=["Finance"])
def list_accounts(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Retrieves all financial accounts for the authenticated user."""
    return db.query(models.Account).filter(
        models.Account.owner_id == current_user.id
    ).all()

@app.post("/api/v1/accounts", tags=["Finance"], status_code=201)
def create_account(
    account_in: schemas.AccountCreate, 
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Initializes a new financial account (e.g., Savings, Checking, Cash)."""
    new_account = models.Account(
        **account_in.dict(), 
        owner_id=current_user.id
    )
    db.add(new_account)
    db.commit()
    db.refresh(new_account)
    
    create_audit_log(
        db, current_user.id, "CREATE_ACCOUNT", new_account.id, 
        f"Initialized account: {new_account.name}"
    )
    db.commit()
    return new_account

# --- Financial Transaction Engine ---

@app.get("/api/v1/transactions", tags=["Finance"])
def list_transactions(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Retrieves and decrypts all transaction records for the authenticated user."""
    db_txs = db.query(models.Transaction).filter(
        models.Transaction.owner_id == current_user.id
    ).order_by(models.Transaction.id.desc()).all()

    # [ENCRYPTION] Decrypt stored strings back to floats for frontend display
    for tx in db_txs:
        tx.amount = auth.decrypt_amount(tx.amount)
    
    return db_txs

@app.post("/api/v1/transactions", tags=["Finance"], status_code=201)
def create_transaction(
    tx_in: schemas.TransactionCreate, 
    db: Session = Depends(get_db), 
    current_user: models.User = Depends(get_current_user)
):
    """Processes a new ledger entry with field-level encryption and balance adjustment."""
    
    # 1. Validate Account & Lock for Update
    account = db.query(models.Account).filter(
        models.Account.id == tx_in.account_id, 
        models.Account.owner_id == current_user.id
    ).with_for_update().first()
    
    if not account:
        raise HTTPException(status_code=404, detail="Account not found.")

    # 2. Update Running Balance
    if tx_in.transaction_type == "income":
        account.balance += tx_in.amount
    else:
        account.balance -= tx_in.amount

    # 3. [ENCRYPTION] Encrypt amount before persistence
    encrypted_val = auth.encrypt_amount(tx_in.amount)

    # 4. Save Encrypted Transaction
    new_tx = models.Transaction(
        description=tx_in.description,
        amount=encrypted_val,
        category=tx_in.category,
        transaction_type=tx_in.transaction_type,
        account_id=tx_in.account_id,
        owner_id=current_user.id
    )
    db.add(new_tx)
    db.flush() 

    # 5. Audit Logging
    create_audit_log(
        db, current_user.id, "CREATE_TX", new_tx.id, 
        f"Processed {tx_in.transaction_type} for account ID {tx_in.account_id}"
    )

    db.commit() 
    db.refresh(new_tx)
    
    # Decrypt for the final response
    new_tx.amount = auth.decrypt_amount(new_tx.amount)
    return new_tx

@app.get("/api/v1/dashboard", tags=["Finance"])
def get_dashboard_summary(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Aggregates financial KPIs by decrypting stored data on-the-fly."""
    txs = db.query(models.Transaction).filter(models.Transaction.owner_id == current_user.id).all()
    
    # [ENCRYPTION] Decrypt each record before calculating sums
    income = sum(auth.decrypt_amount(t.amount) for t in txs if t.transaction_type == "income")
    expense = sum(auth.decrypt_amount(t.amount) for t in txs if t.transaction_type == "expense")
    
    return {"total_income": income, "total_expense": expense, "balance": income - expense}

@app.delete("/api/v1/transactions/{tx_id}", tags=["Finance"])
def delete_transaction(
    tx_id: int, 
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Removes a transaction and logs the security event."""
    tx = db.query(models.Transaction).filter(
        models.Transaction.id == tx_id, 
        models.Transaction.owner_id == current_user.id
    ).first()
    
    if not tx:
        raise HTTPException(status_code=404, detail="Transaction not found.")
    
    create_audit_log(
        db, current_user.id, "DELETE_TX", tx_id, 
        f"Deleted record: {tx.description}"
    )
    
    db.delete(tx)
    db.commit()
    return {"status": "deleted"}

@app.get("/api/v1/audit-logs", tags=["Finance"])
def get_audit_logs(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Retrieves security audit logs for compliance tracking."""
    return db.query(models.AuditLog).filter(
        models.AuditLog.user_id == current_user.id
    ).order_by(models.AuditLog.timestamp.desc()).all()