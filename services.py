from sqlalchemy.orm import Session
from fastapi import HTTPException, status
import models
import schemas
import auth
from datetime import datetime

class LedgerService:
    """
    Business Logic Layer for Financial Operations.
    Handles data integrity, field-level security, and audit trails.
    """

    @staticmethod
    def create_transaction(db: Session, tx_in: schemas.TransactionCreate, user_id: int):
        """
        Processes a new transaction:
        1. Row-level locks the account to prevent balance race conditions.
        2. Updates account balance based on income/expense.
        3. Encrypts the amount before database persistence.
        4. Records a permanent audit log entry.
        """
        # [1] SELECT ... FOR UPDATE to lock the row during calculation
        account = db.query(models.Account).filter(
            models.Account.id == tx_in.account_id,
            models.Account.owner_id == user_id
        ).with_for_update().first()

        if not account:
            raise HTTPException(status_code=404, detail="Account not found.")

        # [2] Update running balance in memory
        if tx_in.transaction_type == "income":
            account.balance += tx_in.amount
        else:
            account.balance -= tx_in.amount

        # [3] AES-256 Encryption for sensitive financial fields
        encrypted_amount = auth.encrypt_amount(tx_in.amount)
        
        # Handle custom date parsing
        tx_date = datetime.now()
        if tx_in.date:
            try:
                tx_date = datetime.strptime(tx_in.date, "%Y-%m-%d")
            except ValueError:
                pass

        new_tx = models.Transaction(
            description=tx_in.description,
            amount=encrypted_amount,
            category=tx_in.category or "General",
            transaction_type=tx_in.transaction_type,
            account_id=tx_in.account_id,
            owner_id=user_id,
            date=tx_date
        )

        try:
            db.add(new_tx)
            db.flush() 

            # [4] Security Audit Logging for compliance
            log = models.AuditLog(
                user_id=user_id,
                action="CREATE_TX",
                target_id=new_tx.id,
                details=f"Added {tx_in.transaction_type}: {tx_in.description} (${tx_in.amount})"
            )
            db.add(log)
            db.commit()
            db.refresh(new_tx)
            
            # Decrypt amount for the final response without affecting DB state
            new_tx.amount = tx_in.amount
            return new_tx
        except Exception as e:
            db.rollback()
            raise HTTPException(status_code=500, detail=f"Database synchronization failed: {str(e)}")

    @staticmethod
    def delete_transaction(db: Session, tx_id: int, user_id: int):
        """
        Removes a transaction and reverts the account balance atomically.
        """
        tx = db.query(models.Transaction).filter(
            models.Transaction.id == tx_id,
            models.Transaction.owner_id == user_id
        ).first()

        if not tx:
            raise HTTPException(status_code=404, detail="Transaction not found.")

        # Revert account balance before deleting the record
        account = db.query(models.Account).filter(models.Account.id == tx.account_id).with_for_update().first()
        if account:
            try:
                raw_amount = float(auth.decrypt_amount(tx.amount))
                if tx.transaction_type == "income":
                    account.balance -= raw_amount
                else:
                    account.balance += raw_amount
            except Exception:
                pass # Integrity fallback if decryption fails

        try:
            log = models.AuditLog(
                user_id=user_id,
                action="DELETE_TX",
                target_id=tx_id,
                details=f"Deleted transaction: {tx.description}"
            )
            db.add(log)
            db.delete(tx)
            db.commit()
            return {"status": "success"}
        except Exception:
            db.rollback()
            raise HTTPException(status_code=500, detail="Deletion failed.")

    @staticmethod
    def delete_account(db: Session, account_id: int, user_id: int):
        """
        Deletes an account and its history. Cascade is handled at DB level.
        """
        account = db.query(models.Account).filter(
            models.Account.id == account_id,
            models.Account.owner_id == user_id
        ).first()

        if not account:
            raise HTTPException(status_code=404, detail="Account not found.")

        try:
            log = models.AuditLog(user_id=user_id, action="DELETE_ACCOUNT", target_id=account_id, details=f"Deleted account: {account.name}")
            db.add(log)
            db.delete(account)
            db.commit()
            return {"status": "success"}
        except Exception:
            db.rollback()
            raise HTTPException(status_code=500, detail="Account removal failed.")

    @staticmethod
    def get_processed_transactions(query_results):
        """
        Maps DB encrypted records to safe Pydantic objects for frontend use.
        Ensures plaintext data is never written back to the database.
        """
        processed = []
        for tx in query_results:
            try:
                decrypted_val = float(auth.decrypt_amount(tx.amount))
            except Exception:
                decrypted_val = 0.0
            
            processed.append(schemas.TransactionSchema(
                id=tx.id,
                description=tx.description,
                amount=decrypted_val,
                category=tx.category,
                transaction_type=tx.transaction_type,
                account_id=tx.account_id,
                date=tx.date,
                owner_id=tx.owner_id
            ))
        return processed
    @staticmethod
    def update_transaction(db: Session, tx_id: int, tx_in: schemas.TransactionCreate, user_id: int):
        """
        Updates an existing transaction:
        1. Calculates the balance difference between the old and new amount.
        2. Updates the associated account balance.
        3. Re-encrypts the new amount.
        """
        # [1] Fetch existing transaction
        tx = db.query(models.Transaction).filter(
            models.Transaction.id == tx_id,
            models.Transaction.owner_id == user_id
        ).with_for_update().first()

        if not tx:
            raise HTTPException(status_code=404, detail="Transaction not found.")

        # [2] Handle Balance Adjustment
        account = db.query(models.Account).filter(models.Account.id == tx.account_id).with_for_update().first()
        if account:
            # Revert old amount
            old_amount = float(auth.decrypt_amount(tx.amount))
            if tx.transaction_type == "income":
                account.balance -= old_amount
            else:
                account.balance += old_amount
            
            # Apply new amount
            if tx_in.transaction_type == "income":
                account.balance += tx_in.amount
            else:
                account.balance -= tx_in.amount

        # [3] Update fields
        tx.description = tx_in.description
        tx.category = tx_in.category
        tx.transaction_type = tx_in.transaction_type
        tx.amount = auth.encrypt_amount(tx_in.amount)
        
        if tx_in.date:
            try:
                tx.date = datetime.strptime(tx_in.date, "%Y-%m-%d")
            except ValueError:
                pass

        try:
            # [4] Audit log for the modification
            log = models.AuditLog(
                user_id=user_id,
                action="UPDATE_TX",
                target_id=tx_id,
                details=f"Updated TX: {tx_in.description} (${tx_in.amount})"
            )
            db.add(log)
            db.commit()
            db.refresh(tx)
            
            tx.amount = tx_in.amount # Decrypt for response
            return tx
        except Exception:
            db.rollback()
            raise HTTPException(status_code=500, detail="Update failed.")