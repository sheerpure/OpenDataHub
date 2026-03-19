import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import os

# Internal Module Imports
from database import Base, get_db
from main import app
import models
import auth

# [1] TEST DATABASE CONFIGURATION
TEST_DATABASE_URL = "sqlite:///./test_fintech.db"

engine = create_engine(
    TEST_DATABASE_URL, 
    connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)

@pytest.fixture(scope="module", autouse=True)
def setup_database():
    """Initializes schema and ensures engine is disposed before deletion."""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)
    # [FIX] Dispose engine to release file lock on Windows
    engine.dispose() 
    
    if os.path.exists("./test_fintech.db"):
        try:
            os.remove("./test_fintech.db")
        except PermissionError:
            print("\n⚠️ Note: Could not delete test DB file due to Windows lock. This is okay.")

# --- FUNCTIONAL TEST SUITE ---

def test_complete_fintech_workflow():
    """INTEGRATION TEST: Verifies the entire financial lifecycle."""
    
    # STEP A: Register & Login
    client.post("/api/v1/auth/register", json={
        "username": "tester", "email": "test@example.com", "password": "password123"
    })
    login_res = client.post("/api/v1/auth/login", data={"username": "tester", "password": "password123"})
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # STEP B: Create Accounts
    acc1 = client.post("/api/v1/accounts", headers=headers, json={"name": "Bank", "balance": 1000.0}).json()
    acc2 = client.post("/api/v1/accounts", headers=headers, json={"name": "Cash", "balance": 50.0}).json()
    
    # STEP C: Atomic Fund Transfer
    transfer_payload = {
        "from_account_id": acc1["id"],
        "to_account_id": acc2["id"],
        "amount": 200.0,
        "description": "Internal test transfer"
    }
    client.post("/api/v1/transfers", headers=headers, json=transfer_payload)

    # STEP D: Reconciliation
    updated_accs = client.get("/api/v1/accounts", headers=headers).json()
    bank = next(a for a in updated_accs if a["id"] == acc1["id"])
    cash = next(a for a in updated_accs if a["id"] == acc2["id"])
    
    assert bank["balance"] == 800.0
    assert cash["balance"] == 250.0

    # STEP E: Ledger Verification
    tx_res = client.get("/api/v1/transactions", headers=headers).json()
    
    # [FIX] Handling both Paginated Object and Raw List
    tx_list = tx_res["items"] if isinstance(tx_res, dict) and "items" in tx_res else tx_res
    
    assert len(tx_list) >= 2
    assert any(t["category"] == "Transfer" for t in tx_list)
    
    print("\n✅ End-to-End Financial Workflow Verified!")

def test_overdraft_prevention():
    """SECURITY TEST: Prevents overdrafts."""
    login_res = client.post("/api/v1/auth/login", data={"username": "tester", "password": "password123"})
    headers = {"Authorization": f"Bearer {login_res.json()['access_token']}"}
    
    res = client.post("/api/v1/transfers", headers=headers, json={
        "from_account_id": 1, "to_account_id": 2, "amount": 5000.0
    })
    assert res.status_code == 400
    print("✅ Overdraft Security Policy Verified!")