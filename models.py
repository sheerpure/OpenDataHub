from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime
from database import Base

class User(Base):
    """
    User Management: Stores identity and provides relations to financial data.
    """
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)

    # Relationships
    accounts = relationship("Account", back_populates="owner")
    transactions = relationship("Transaction", back_populates="owner")
    audit_logs = relationship("AuditLog", back_populates="user_ref")

class Transaction(Base):
    """
    Transaction Ledger: The core data model for income and expense records.
    """
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    description = Column(String)  
    amount = Column(String)       
    category = Column(String)    
    transaction_type = Column(String) # 'income' or 'expense'
    date = Column(DateTime, server_default=func.now())
    owner_id = Column(Integer, ForeignKey("users.id"))
    account_id = Column(Integer, ForeignKey("accounts.id"))
    account = relationship("Account", back_populates="transactions")

    # Relationship to User
    owner = relationship("User", back_populates="transactions")

class AuditLog(Base):
    """
    Audit Trail: Permanent log of sensitive operations (Create/Delete).
    Critical for financial compliance and accountability.
    """
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    action = Column(String)      # e.g., "CREATE", "DELETE"
    target_id = Column(Integer)  # ID of the affected transaction
    details = Column(String)     # Human-readable change summary
    timestamp = Column(DateTime, default=datetime.utcnow)

    # Relationship back to User
    user_ref = relationship("User", back_populates="audit_logs")

class Account(Base):
    """
    Financial Accounts: Separate containers for funds (e.g., Cash, Bank, Savings).
    Tracks real-time balance for each account.
    """
    __tablename__ = "accounts"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True) # 帳戶名稱：如 "Cash", "E.SUN Bank"
    balance = Column(Float, default=0.0)
    account_type = Column(String) # "Checking", "Savings", "Credit Card"
    owner_id = Column(Integer, ForeignKey("users.id"))

    owner = relationship("User", back_populates="accounts")
    transactions = relationship("Transaction", back_populates="account")