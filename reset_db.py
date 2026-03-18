from sqlalchemy import text
from database import engine, Base 
import models

def reset_database():
    print("⚠️  Warning: This will PERMANENTLY DELETE all data from your SQLite database!")
    confirm = input("Are you sure? (y/n): ")
    
    if confirm.lower() == 'y':
        with engine.connect() as conn:
            print("Force dropping all tables...")
            
            # List tables in order: Drop child tables (with Foreign Keys) first
            tables = ["audit_logs", "transactions", "accounts", "datasets", "users"]
            
            for table in tables:
                try:
                    conn.execute(text(f"DROP TABLE IF EXISTS {table};"))
                    print(f" - Dropped table: {table}")
                except Exception as e:
                    print(f" - Error dropping {table}: {e}")
            
            conn.commit()
        
        # Now recreate the tables based on your current models.py
        print("Recreating tables from current models...")
        models.Base.metadata.create_all(bind=engine)
        
        print("\n✅ Database Cleaned and Re-aligned! You can now start the server.")
    else:
        print("Operation cancelled.")

if __name__ == "__main__":
    reset_database()