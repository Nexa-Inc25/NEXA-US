#!/usr/bin/env python3
"""
Generate secure credentials for NEXA AI Document Analyzer
Run this to create production-ready security keys
"""

import secrets
import string
from cryptography.fernet import Fernet
from passlib.context import CryptContext
from datetime import datetime
import os

print("="*70)
print("NEXA SECURITY CREDENTIAL GENERATOR")
print("="*70)
print(f"Generated: {datetime.now().isoformat()}")
print("-"*70)

def generate_jwt_secret():
    """Generate secure JWT secret"""
    return secrets.token_urlsafe(32)

def generate_encryption_key():
    """Generate Fernet encryption key"""
    return Fernet.generate_key().decode()

def generate_secure_password(length=16):
    """Generate secure random password"""
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*()_+-="
    password = ''.join(secrets.choice(alphabet) for _ in range(length))
    return password

def hash_password(password):
    """Hash password with bcrypt"""
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    return pwd_context.hash(password)

# Generate all credentials
credentials = {
    "JWT_SECRET": generate_jwt_secret(),
    "ENCRYPTION_KEY": generate_encryption_key(),
    "ADMIN_PASSWORD": generate_secure_password(20),
    "DATABASE_PASSWORD": generate_secure_password(24),
    "API_KEY": secrets.token_urlsafe(32),
    "WEBHOOK_SECRET": secrets.token_hex(32)
}

# Display credentials
print("\n📋 PRODUCTION CREDENTIALS (Save these securely!)")
print("-"*70)

for key, value in credentials.items():
    print(f"\n{key}:")
    print(f"  {value}")
    if key == "ADMIN_PASSWORD":
        print(f"  Hashed: {hash_password(value)[:20]}...")

# Generate .env file content
env_content = f"""# NEXA AI Document Analyzer - Production Environment
# Generated: {datetime.now().isoformat()}
# SECURITY CRITICAL: Save these credentials securely!

# === SECURITY (Required) ===
JWT_SECRET={credentials['JWT_SECRET']}
ENCRYPTION_KEY={credentials['ENCRYPTION_KEY']}
ADMIN_PASSWORD={credentials['ADMIN_PASSWORD']}

# === DATABASE ===
# Render PostgreSQL (internal URL for production)
DATABASE_URL=postgresql://nexa_db_94sr_user:{credentials['DATABASE_PASSWORD']}@dpg-d3mifuili9vc73a8a9kg-a/nexa_db_94sr

# === API KEYS ===
API_KEY={credentials['API_KEY']}
WEBHOOK_SECRET={credentials['WEBHOOK_SECRET']}

# === SECURITY SETTINGS ===
JWT_ALGORITHM=HS256
JWT_EXPIRATION_HOURS=24
ENABLE_AUDIT_LOGGING=true
RATE_LIMIT_PER_MINUTE=100

# === CORS (Update for production) ===
CORS_ORIGINS=https://your-frontend-domain.com,https://nexa-dashboard.com

# === SERVICE CONFIG ===
MAX_LOGIN_ATTEMPTS=5
ACCOUNT_LOCKOUT_MINUTES=15
PASSWORD_MIN_LENGTH=12
REQUIRE_MFA=false
"""

# Write to .env.production file
output_file = ".env.production"
with open(output_file, "w") as f:
    f.write(env_content)

print(f"\n✅ Environment file written to: {output_file}")

# Generate Render.com environment variable commands
print("\n" + "="*70)
print("RENDER.COM ENVIRONMENT VARIABLES")
print("="*70)
print("\nCopy and paste these into Render.com dashboard:")
print("-"*70)

render_vars = [
    f"JWT_SECRET={credentials['JWT_SECRET']}",
    f"ENCRYPTION_KEY={credentials['ENCRYPTION_KEY']}",
    f"ADMIN_PASSWORD={credentials['ADMIN_PASSWORD']}",
    f"API_KEY={credentials['API_KEY']}",
    f"WEBHOOK_SECRET={credentials['WEBHOOK_SECRET']}",
    "JWT_ALGORITHM=HS256",
    "JWT_EXPIRATION_HOURS=24",
    "ENABLE_AUDIT_LOGGING=true",
    "RATE_LIMIT_PER_MINUTE=100"
]

for var in render_vars:
    print(var)

# Security checklist
print("\n" + "="*70)
print("🔒 SECURITY CHECKLIST")
print("="*70)

checklist = [
    "Save these credentials in a secure password manager",
    "Never commit .env.production to Git",
    "Add .env* to .gitignore",
    "Set all environment variables in Render.com",
    "Change admin password after first login",
    "Enable HTTPS on Render (automatic)",
    "Configure production CORS origins",
    "Set up monitoring alerts",
    "Enable database backups",
    "Review audit logs weekly",
    "Rotate secrets quarterly",
    "Test all security features before go-live"
]

for i, item in enumerate(checklist, 1):
    print(f"{i:2}. [ ] {item}")

print("\n" + "="*70)
print("⚠️ IMPORTANT: These credentials are generated only once!")
print("Save them immediately in a secure location.")
print("="*70)
