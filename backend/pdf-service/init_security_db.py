#!/usr/bin/env python3
"""
Initialize NEXA Security Database
Creates users, audit_logs tables and initial admin user
"""

import os
import sys
from datetime import datetime
from sqlalchemy import create_engine, text
from passlib.context import CryptContext
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

print("="*70)
print("NEXA SECURITY DATABASE INITIALIZATION")
print("="*70)
print(f"Time: {datetime.now().isoformat()}")
print("-"*70)

# Database configuration
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    # Use Render PostgreSQL for production
    DATABASE_URL = "postgresql://nexa_db_94sr_user:H9AZevmgdNd5pWEFVkTm880HX5A6ATzd@dpg-d3mifuili9vc73a8a9kg-a.oregon-postgres.render.com/nexa_db_94sr"
    print("⚠️ Using default database URL. Set DATABASE_URL for production.")

# Fix postgres:// to postgresql://
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

print(f"\n📍 Database: {DATABASE_URL.split('@')[1] if '@' in DATABASE_URL else 'local'}")

def create_tables():
    """Create security tables"""
    
    engine = create_engine(DATABASE_URL)
    
    # SQL for creating tables
    sql_statements = [
        # Users table
        """
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            username VARCHAR(100) UNIQUE NOT NULL,
            email VARCHAR(255) UNIQUE NOT NULL,
            hashed_password VARCHAR(255) NOT NULL,
            full_name VARCHAR(255),
            role VARCHAR(50) DEFAULT 'viewer',
            company VARCHAR(100) DEFAULT 'PG&E',
            is_active BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_login TIMESTAMP,
            failed_attempts INTEGER DEFAULT 0,
            locked_until TIMESTAMP,
            created_by VARCHAR(100),
            CONSTRAINT valid_role CHECK (role IN ('admin', 'manager', 'analyst', 'viewer'))
        )
        """,
        
        # Create indexes for performance
        "CREATE INDEX IF NOT EXISTS idx_users_username ON users(username)",
        "CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)",
        "CREATE INDEX IF NOT EXISTS idx_users_role ON users(role)",
        
        # Audit logs table
        """
        CREATE TABLE IF NOT EXISTS audit_logs (
            id SERIAL PRIMARY KEY,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            user_id INTEGER REFERENCES users(id),
            username VARCHAR(100),
            action VARCHAR(100) NOT NULL,
            resource VARCHAR(255),
            pm_number VARCHAR(50),
            status VARCHAR(20),
            ip_address VARCHAR(45),
            user_agent TEXT,
            details JSONB,
            duration_ms INTEGER
        )
        """,
        
        # Create indexes for audit logs
        "CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON audit_logs(timestamp DESC)",
        "CREATE INDEX IF NOT EXISTS idx_audit_user ON audit_logs(user_id)",
        "CREATE INDEX IF NOT EXISTS idx_audit_action ON audit_logs(action)",
        "CREATE INDEX IF NOT EXISTS idx_audit_pm ON audit_logs(pm_number)",
        
        # API keys table for mobile/external access
        """
        CREATE TABLE IF NOT EXISTS api_keys (
            id SERIAL PRIMARY KEY,
            key_hash VARCHAR(255) UNIQUE NOT NULL,
            user_id INTEGER REFERENCES users(id),
            name VARCHAR(100) NOT NULL,
            description TEXT,
            permissions JSONB,
            last_used TIMESTAMP,
            expires_at TIMESTAMP,
            is_active BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            created_by VARCHAR(100)
        )
        """,
        
        # Session management table
        """
        CREATE TABLE IF NOT EXISTS user_sessions (
            id SERIAL PRIMARY KEY,
            user_id INTEGER REFERENCES users(id),
            token_hash VARCHAR(255) UNIQUE NOT NULL,
            ip_address VARCHAR(45),
            user_agent TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            expires_at TIMESTAMP,
            revoked BOOLEAN DEFAULT FALSE
        )
        """,
        
        # Role permissions table
        """
        CREATE TABLE IF NOT EXISTS role_permissions (
            id SERIAL PRIMARY KEY,
            role VARCHAR(50) NOT NULL,
            resource VARCHAR(100) NOT NULL,
            action VARCHAR(50) NOT NULL,
            allowed BOOLEAN DEFAULT TRUE,
            UNIQUE(role, resource, action)
        )
        """
    ]
    
    # Execute SQL statements
    with engine.connect() as conn:
        for sql in sql_statements:
            try:
                conn.execute(text(sql))
                conn.commit()
                print(f"✅ Executed: {sql.split('(')[0].strip()}")
            except Exception as e:
                print(f"⚠️ Warning: {e}")
    
    print("\n✅ Security tables created successfully")
    return engine

def insert_default_permissions(engine):
    """Insert default role permissions"""
    
    permissions = [
        # Admin - full access
        ('admin', 'users', 'create', True),
        ('admin', 'users', 'read', True),
        ('admin', 'users', 'update', True),
        ('admin', 'users', 'delete', True),
        ('admin', 'documents', 'upload', True),
        ('admin', 'documents', 'analyze', True),
        ('admin', 'asbuilts', 'generate', True),
        ('admin', 'audit_logs', 'read', True),
        
        # Manager - most operations
        ('manager', 'users', 'read', True),
        ('manager', 'documents', 'upload', True),
        ('manager', 'documents', 'analyze', True),
        ('manager', 'asbuilts', 'generate', True),
        ('manager', 'audit_logs', 'read', False),
        
        # Analyst - read and analyze
        ('analyst', 'documents', 'upload', True),
        ('analyst', 'documents', 'analyze', True),
        ('analyst', 'asbuilts', 'generate', False),
        
        # Viewer - read only
        ('viewer', 'documents', 'read', True),
        ('viewer', 'asbuilts', 'read', True),
    ]
    
    with engine.connect() as conn:
        for role, resource, action, allowed in permissions:
            sql = """
                INSERT INTO role_permissions (role, resource, action, allowed)
                VALUES (:role, :resource, :action, :allowed)
                ON CONFLICT (role, resource, action) DO NOTHING
            """
            conn.execute(text(sql), {
                'role': role,
                'resource': resource,
                'action': action,
                'allowed': allowed
            })
        conn.commit()
    
    print("✅ Default role permissions inserted")

def create_initial_users(engine):
    """Create initial admin and test users"""
    
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    
    # Get admin password from environment or use default
    admin_password = os.getenv("ADMIN_PASSWORD", "ChangeMe123!@#")
    
    users = [
        {
            'username': 'admin',
            'email': 'admin@nexa.com',
            'password': admin_password,
            'full_name': 'System Administrator',
            'role': 'admin',
            'company': 'NEXA'
        },
        {
            'username': 'pm_mike',
            'email': 'mike@pge.com',
            'password': 'SecurePM123!@#',
            'full_name': 'Mike Johnson',
            'role': 'manager',
            'company': 'PG&E'
        },
        {
            'username': 'analyst_sarah',
            'email': 'sarah@pge.com',
            'password': 'SecureAnalyst123!@#',
            'full_name': 'Sarah Chen',
            'role': 'analyst',
            'company': 'PG&E'
        }
    ]
    
    with engine.connect() as conn:
        for user_data in users:
            # Check if user exists
            result = conn.execute(
                text("SELECT id FROM users WHERE username = :username"),
                {'username': user_data['username']}
            ).first()
            
            if not result:
                # Hash password
                hashed_password = pwd_context.hash(user_data['password'])
                
                # Insert user
                sql = """
                    INSERT INTO users (
                        username, email, hashed_password, 
                        full_name, role, company
                    ) VALUES (
                        :username, :email, :hashed_password,
                        :full_name, :role, :company
                    )
                """
                conn.execute(text(sql), {
                    'username': user_data['username'],
                    'email': user_data['email'],
                    'hashed_password': hashed_password,
                    'full_name': user_data['full_name'],
                    'role': user_data['role'],
                    'company': user_data['company']
                })
                conn.commit()
                print(f"✅ Created user: {user_data['username']} ({user_data['role']})")
            else:
                print(f"ℹ️ User already exists: {user_data['username']}")
    
    print("\n📝 Initial Users Created:")
    print("-"*40)
    print("Username        | Password           | Role")
    print("-"*40)
    print(f"admin           | {admin_password}    | admin")
    print("pm_mike         | SecurePM123!@#     | manager")
    print("analyst_sarah   | SecureAnalyst123!@# | analyst")
    print("-"*40)
    print("\n⚠️ CHANGE THESE PASSWORDS IMMEDIATELY!")

def verify_setup(engine):
    """Verify security setup"""
    
    with engine.connect() as conn:
        # Check tables
        tables = ['users', 'audit_logs', 'api_keys', 'user_sessions', 'role_permissions']
        for table in tables:
            result = conn.execute(
                text(f"SELECT COUNT(*) FROM {table}")
            ).scalar()
            print(f"  • {table}: {result} records")
        
        # Check admin user
        result = conn.execute(
            text("SELECT username, role FROM users WHERE role = 'admin'")
        ).first()
        if result:
            print(f"\n✅ Admin user ready: {result[0]}")
        else:
            print("\n❌ No admin user found!")

def main():
    """Main initialization"""
    
    try:
        # Create tables
        engine = create_tables()
        
        # Insert permissions
        insert_default_permissions(engine)
        
        # Create users
        create_initial_users(engine)
        
        # Verify
        print("\n" + "="*70)
        print("VERIFICATION")
        print("="*70)
        verify_setup(engine)
        
        print("\n" + "="*70)
        print("✅ SECURITY DATABASE INITIALIZED")
        print("="*70)
        print("\nNext steps:")
        print("1. Test login with admin credentials")
        print("2. Change default passwords")
        print("3. Create production user accounts")
        print("4. Enable audit logging")
        print("5. Configure API keys for mobile app")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
