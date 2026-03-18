# reset_db.py
from sqlalchemy import text
from database import engine
import models

def reset_database():
    print("⚠️  Warning: This will perform a CASCADE delete on ALL tables!")
    confirm = input("Are you sure? (y/n): ")
    
    if confirm.lower() == 'y':
        with engine.connect() as conn:
            # PostgreSQL command to drop all tables in the public schema
            print("Force dropping all tables with CASCADE...")
            # This SQL command finds all tables and drops them with CASCADE
            conn.execute(text("""
                DROP TABLE IF EXISTS audit_logs CASCADE;
                DROP TABLE IF EXISTS transactions CASCADE;
                DROP TABLE IF EXISTS accounts CASCADE;
                DROP TABLE IF EXISTS datasets CASCADE;
                DROP TABLE IF EXISTS users CASCADE;
            """))
            conn.commit()
        
        # Now recreate the tables based on your current models.py
        print("Recreating tables from current models...")
        models.Base.metadata.create_all(bind=engine)
        
        print("✅ Database Cleaned and Re-aligned! You can now start Uvicorn.")
    else:
        print("Operation cancelled.")

if __name__ == "__main__":
    reset_database()