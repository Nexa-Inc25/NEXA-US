"""
Test PostgreSQL Connection for NEXA AI Document Analyzer
Run this to verify your database is properly configured
"""

import psycopg2
import os

# Your actual connection string
DATABASE_URL = "postgresql://nexa_admin:h7L101QmZt1WTyVHrnm4rLOz2wKRVF4G@dpg-d3hh2i63jp1c73fht4hg-a.oregon-postgres.render.com/nexa_aerh"

def test_connection():
    """Test database connection and pgvector extension"""
    try:
        print("🔄 Connecting to PostgreSQL...")
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()
        
        # Test basic connection
        cursor.execute("SELECT version();")
        version = cursor.fetchone()
        print(f"✅ Connected! PostgreSQL version: {version[0][:50]}...")
        
        # Check if pgvector is installed
        cursor.execute("SELECT * FROM pg_extension WHERE extname = 'vector';")
        vector_ext = cursor.fetchone()
        
        if vector_ext:
            print("✅ pgvector extension is installed!")
        else:
            print("⚠️ pgvector not installed. Installing now...")
            cursor.execute("CREATE EXTENSION IF NOT EXISTS vector;")
            conn.commit()
            print("✅ pgvector extension installed!")
        
        # Check tables
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            ORDER BY table_name;
        """)
        tables = cursor.fetchall()
        
        if tables:
            print(f"\n📊 Existing tables:")
            for table in tables:
                print(f"   - {table[0]}")
        else:
            print("\n📊 No tables yet (they'll be created when API starts)")
        
        # Create tables if they don't exist
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS spec_chunks (
                id SERIAL PRIMARY KEY,
                text TEXT NOT NULL,
                embedding vector(384),
                section_reference VARCHAR(100),
                source_file VARCHAR(255),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS audit_log (
                id SERIAL PRIMARY KEY,
                user_id VARCHAR(100),
                action VARCHAR(100),
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                details JSONB
            );
        """)
        
        conn.commit()
        print("\n✅ Tables created/verified!")
        
        # Test vector operations
        print("\n🧪 Testing vector operations...")
        cursor.execute("SELECT vector_dims(ARRAY[1,2,3]::vector);")
        result = cursor.fetchone()
        print(f"✅ Vector test successful! Dimension: {result[0]}")
        
        cursor.close()
        conn.close()
        
        print("\n🎉 Database is fully configured and ready!")
        print(f"\n📝 Add this to your Render environment variables:")
        print(f"DATABASE_URL={DATABASE_URL}")
        
    except psycopg2.OperationalError as e:
        print(f"❌ Connection failed: {e}")
        print("\nTroubleshooting:")
        print("1. Check if database is active in Render dashboard")
        print("2. Verify the connection string is correct")
        print("3. Ensure your IP is allowed (if using external connection)")
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_connection()
