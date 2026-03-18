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

from fastapi import FastAPI, Depends, Request, HTTPException, status, Response
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from sqlalchemy import or_, func
from fastapi.security import OAuth2PasswordRequestForm
from pathlib import Path
from typing import Optional
from datetime import datetime
import csv
import io

# Internal module imports
from database import get_db, engine
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
    version="1.2.0",
    docs_url="/api/v1/docs",
    redoc_url=None
)

# Database Synchronization on Startup
@app.on_event("startup")
def configure_db():
    models.Base.metadata.create_all(bind=engine)

# --- Frontend Shell (SSR) ---

@app.get("/", response_class=HTMLResponse, tags=["Frontend"])
async def home(request: Request):
    """Serves the main SPA Dashboard."""
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/login", response_class=HTMLResponse, tags=["Frontend"])
async def login_page(request: Request):
    """Serves the login page."""
    return templates.TemplateResponse("login.html", {"request": request})

@app.get("/register", response_class=HTMLResponse, tags=["Frontend"])
async def register_page(request: Request):
    """Serves the registration page."""
    return templates.TemplateResponse("register.html", {"request": request})

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
    """Initializes a new financial account with unique name check and audit trail."""
    # 1. [UNIQUE CHECK] Prevent duplicate account names for the same user
    existing_acc = db.query(models.Account).filter(
        models.Account.owner_id == current_user.id,
        models.Account.name == account_in.name
    ).first()
    
    if existing_acc:
        raise HTTPException(status_code=400, detail="Account name already exists.")

    new_account = models.Account(
        **account_in.dict(), 
        owner_id=current_user.id
    )
    db.add(new_account)
    db.commit()
    db.refresh(new_account)
    
    create_audit_log(db, current_user.id, "CREATE_ACCOUNT", new_account.id, f"Created: {new_account.name}")
    db.commit()
    return new_account

@app.delete("/api/v1/accounts/{account_id}", tags=["Finance"])
def delete_account(
    account_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Deletes an account and all its associated transactions (Cascade)."""
    account = db.query(models.Account).filter(
        models.Account.id == account_id,
        models.Account.owner_id == current_user.id
    ).first()

    if not account:
        raise HTTPException(status_code=404, detail="Account not found.")

    create_audit_log(db, current_user.id, "DELETE_ACCOUNT", account_id, f"Deleted account: {account.name}")
    db.delete(account)
    db.commit()
    return {"status": "success", "message": f"Account {account_id} deleted."}

# --- Financial Transaction Engine ---

@app.get("/api/v1/transactions", tags=["Finance"])
def list_transactions(
    account_id: Optional[int] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    sort_by: Optional[str] = "date_desc",
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Fetches transaction history with multi-layered filtering and logic-level sorting.
    Handles date range extraction and decrypts sensitive financial data.
    """
    # [1] BASE QUERY: Restrict records to the authenticated owner only
    query = db.query(models.Transaction).filter(models.Transaction.owner_id == current_user.id)
    
    # [2] ACCOUNT FILTER: Filter by specific account if provided
    if account_id:
        query = query.filter(models.Transaction.account_id == account_id)
    
    # [3] DATE FILTERS: Clean input and apply range constraints
    if start_date and start_date.strip():
        try:
            # Parse start date at the beginning of the day (00:00:00)
            sd = datetime.strptime(start_date, "%Y-%m-%d")
            query = query.filter(models.Transaction.date >= sd)
        except ValueError:
            pass

    if end_date and end_date.strip():
        try:
            # Set end date to the very last second of the day (23:59:59) for inclusivity
            ed = datetime.strptime(end_date, "%Y-%m-%d").replace(hour=23, minute=59, second=59)
            query = query.filter(models.Transaction.date <= ed)
        except ValueError:
            pass
    
    # [4] DATA FETCHING: Execute query and retrieve raw results
    db_txs = query.all()

    # [5] DECRYPTION & NUMERIC CASTING:
    # Since 'amount' is stored as an encrypted string, it must be decrypted 
    # and converted to float in memory before sorting can happen correctly.
    processed_txs = []
    for tx in db_txs:
        try:
            # auth.decrypt_amount returns the plaintext value
            tx.amount = float(auth.decrypt_amount(tx.amount))
        except Exception:
            # Safety fallback for corrupt data or decryption key mismatch
            tx.amount = 0.0
        processed_txs.append(tx)

    # [6] LOGIC-LEVEL SORTING: Perform final sort in Python for numeric accuracy
    if sort_by == "date_asc":
        processed_txs.sort(key=lambda x: x.date)
    elif sort_by == "date_desc":
        processed_txs.sort(key=lambda x: x.date, reverse=True)
    elif sort_by == "amount_asc":
        processed_txs.sort(key=lambda x: x.amount)
    elif sort_by == "amount_desc":
        processed_txs.sort(key=lambda x: x.amount, reverse=True)
    else:
        # Default fallback to newest first
        processed_txs.sort(key=lambda x: x.date, reverse=True)
    
    return processed_txs

@app.get("/api/v1/transactions/export", tags=["Finance"])
def export_transactions(
    account_id: Optional[int] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Exports decrypted transactions to a CSV file."""
    txs = list_transactions(account_id, start_date, end_date, db, current_user)
    
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Date", "Description", "Category", "Type", "Amount"])
    
    for t in txs:
        prefix = "+" if t.transaction_type == "income" else "-"
        writer.writerow([
            t.date.strftime("%Y-%m-%d %H:%M"),
            t.description,
            t.category or "General",
            t.transaction_type.upper(),
            f"{prefix}{t.amount}"
        ])
    
    response = Response(content=output.getvalue(), media_type="text/csv")
    filename = f"ledger_export_{datetime.now().strftime('%Y%m%d')}.csv"
    response.headers["Content-Disposition"] = f"attachment; filename={filename}"
    
    create_audit_log(db, current_user.id, "EXPORT_CSV", 0, f"Exported {len(txs)} records")
    db.commit()
    return response

@app.post("/api/v1/transactions", tags=["Finance"], status_code=201)
def create_transaction(
    tx_in: schemas.TransactionCreate, 
    db: Session = Depends(get_db), 
    current_user: models.User = Depends(get_current_user)
):
    """
    Creates a new transaction entry with row-level locks and encrypted storage.
    Synchronizes account balance and preserves accurate local time metadata.
    """
    # [1] DATA INTEGRITY: Lock account row to prevent race conditions during balance update
    account = db.query(models.Account).filter(
        models.Account.id == tx_in.account_id, 
        models.Account.owner_id == current_user.id
    ).with_for_update().first()
    
    if not account:
        raise HTTPException(status_code=404, detail="Target account not found.")

    # [2] BALANCE UPDATE: Calculate new running balance based on transaction type
    if tx_in.transaction_type == "income":
        account.balance += tx_in.amount
    else:
        account.balance -= tx_in.amount

    # [3] LOCAL TIME HANDLING: 
    # Prevent UTC-to-Local conversion shifts. We combine the user-selected date 
    # with the current server time to maintain chronological sorting within a single day.
    now_time = datetime.now().time()
    if tx_in.date and tx_in.date.strip():
        try:
            # Extract only the date part and combine with current H:M:S
            selected_date = datetime.strptime(tx_in.date, "%Y-%m-%d").date()
            tx_date = datetime.combine(selected_date, now_time)
        except ValueError:
            tx_date = datetime.now()
    else:
        tx_date = datetime.now()

    # [4] ENCRYPTION: Only encrypt the amount once to prevent nested encryption errors
    encrypted_amount = auth.encrypt_amount(tx_in.amount)

    # [5] PERSISTENCE: Instantiate the Transaction object
    new_tx = models.Transaction(
        description=tx_in.description, 
        amount=encrypted_amount,
        category=tx_in.category or "General", 
        transaction_type=tx_in.transaction_type,
        account_id=tx_in.account_id, 
        owner_id=current_user.id,
        date=tx_date  
    )
    
    db.add(new_tx)
    db.flush() # Sync with DB session to generate the new transaction ID

    # [6] AUDIT TRAIL: Record action for compliance and security monitoring
    create_audit_log(
        db, current_user.id, "CREATE_TX", new_tx.id, 
        f"Processed {tx_in.transaction_type} of {tx_in.amount} for {account.name}"
    )

    # [7] FINALIZATION: Commit transaction and return decrypted object for UI rendering
    db.commit() 
    db.refresh(new_tx)
    
    # Decrypt locally so the frontend receives a readable numeric value immediately
    new_tx.amount = float(auth.decrypt_amount(new_tx.amount))
    return new_tx

@app.get("/api/v1/dashboard", tags=["Finance"])
def get_dashboard_summary(
    account_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Aggregates financial KPIs with decryption and optional account filtering."""
    tx_query = db.query(models.Transaction).filter(models.Transaction.owner_id == current_user.id)
    
    if account_id:
        tx_query = tx_query.filter(models.Transaction.account_id == account_id)
        account = db.query(models.Account).filter(models.Account.id == account_id).first()
        total_balance = account.balance if account else 0
    else:
        total_balance = db.query(func.sum(models.Account.balance)).filter(
            models.Account.owner_id == current_user.id
        ).scalar() or 0

    txs = tx_query.all()
    income = sum(auth.decrypt_amount(t.amount) for t in txs if t.transaction_type == "income")
    expense = sum(auth.decrypt_amount(t.amount) for t in txs if t.transaction_type == "expense")
    
    return {"total_income": income, "total_expense": expense, "balance": total_balance}

@app.delete("/api/v1/transactions/{tx_id}", tags=["Finance"])
def delete_transaction(
    tx_id: int, 
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Removes a transaction and Reverts account balance."""
    tx = db.query(models.Transaction).filter(
        models.Transaction.id == tx_id, 
        models.Transaction.owner_id == current_user.id
    ).first()
    
    if not tx:
        raise HTTPException(status_code=404, detail="Transaction not found.")
    
    account = db.query(models.Account).filter(models.Account.id == tx.account_id).with_for_update().first()
    raw_amount = auth.decrypt_amount(tx.amount)
    
    if tx.transaction_type == "income":
        account.balance -= raw_amount
    else:
        account.balance += raw_amount

    create_audit_log(db, current_user.id, "DELETE_TX", tx_id, f"Deleted: {tx.description}")
    db.delete(tx)
    db.commit()
    return {"status": "deleted"}

@app.get("/api/v1/analytics/category-distribution", tags=["Finance"])
def get_category_distribution(
    account_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Aggregates expense by category."""
    query = db.query(models.Transaction).filter(
        models.Transaction.owner_id == current_user.id,
        models.Transaction.transaction_type == "expense"
    )
    if account_id:
        query = query.filter(models.Transaction.account_id == account_id)

    txs = query.all()
    stats = {}
    for tx in txs:
        amount = auth.decrypt_amount(tx.amount)
        category = tx.category or "Uncategorized"
        stats[category] = stats.get(category, 0) + amount

    return [{"category": cat, "amount": amt} for cat, amt in stats.items()]

@app.get("/api/v1/audit-logs", tags=["Finance"])
def get_audit_logs(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Retrieves security audit logs."""
    return db.query(models.AuditLog).filter(
        models.AuditLog.user_id == current_user.id
    ).order_by(models.AuditLog.timestamp.desc()).all()