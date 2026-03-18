"""
FinTechHub - Internal Database Auditor Tool
Purpose: Direct inspection of encrypted transaction data and security audit logs.
"""

from database import SessionLocal
import models
from datetime import datetime

# Initialize Database Session
db = SessionLocal()

def inspect_database():
    print(f"\n{'='*30} DATABASE INSPECTION {'='*30}")

    print(f"\n[SECTION 0: CURRENT ACCOUNT BALANCES]")
    print(f"{'Account Name':<15} | {'Balance (Live)'}")
    print("-" * 40)
    accounts = db.query(models.Account).all()
    for acc in accounts:
        # These are stored as Floats, so they are not encrypted in the DB
        print(f"{acc.name:<15} | ${acc.balance:,.2f}")

    # --- Section 1: Encrypted Transactions ---
    print(f"\n[SECTION 1: ENCRYPTED LEDGER]")
    print(f"{'Description':<15} | {'Encrypted Amount (Raw Ciphertext)'}")
    print("-" * 80)
    
    # Query all transactions from the database
    transactions = db.query(models.Transaction).all()
    for tx in transactions:
        # Displaying the raw encrypted string to verify field-level encryption (AES)
        print(f"{tx.description:<15} | {tx.amount}")

    # --- Section 2: Security Audit Logs ---
    print(f"\n[SECTION 2: SECURITY AUDIT TRAIL]")
    print(f"{'Timestamp':<20} | {'Action':<15} | {'Audit Details'}")
    print("-" * 80)
    
    # Query audit logs sorted by most recent first for forensic analysis
    logs = db.query(models.AuditLog).order_by(models.AuditLog.timestamp.desc()).all()
    for log in logs:
        # Format timestamp for better readability in the terminal
        time_str = log.timestamp.strftime("%Y-%m-%d %H:%M:%S")
        print(f"{time_str:<20} | {log.action:<15} | {log.details}")

    print(f"\n{'='*81}\n")

if __name__ == "__main__":
    try:
        inspect_database()
    finally:
        # Always close the session to prevent memory leaks or connection hanging
        db.close()