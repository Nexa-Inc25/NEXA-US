"""
Database Migration Script
Run with: python scripts/run-migration.py
"""

import psycopg2
import os

# Your database URL
DB_URL = "postgresql://nexa_core_db_user:yoXdJC1QM8gbKtHNIqLBFyfl8ogPlrsr@dpg-d3iqhdc9c44c73b0bug0-a.oregon-postgres.render.com/nexa_core_db"

def run_migration():
    print("🔄 Connecting to database...")
    
    try:
        # Connect to database
        conn = psycopg2.connect(DB_URL)
        cursor = conn.cursor()
        
        print("📖 Reading schema file...")
        with open('db/schema.sql', 'r') as f:
            schema = f.read()
        
        print("🚀 Running migration...")
        cursor.execute(schema)
        conn.commit()
        
        print("✅ Migration complete!")
        
        # Verify
        print("\n🔍 Verifying tables...")
        cursor.execute("SELECT COUNT(*) FROM users")
        user_count = cursor.fetchone()[0]
        print(f"✅ Users table created with {user_count} seed users")
        
        cursor.close()
        conn.close()
        
        print("\n🎉 Database is ready!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False
    
    return True

if __name__ == "__main__":
    run_migration()
