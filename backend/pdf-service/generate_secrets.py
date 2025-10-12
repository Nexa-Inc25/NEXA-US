#!/usr/bin/env python3
"""
Generate secure secrets for NEXA production deployment
Run this to create secure keys for your .env file
"""

import secrets
import string
from cryptography.fernet import Fernet
import base64
import os

def generate_fernet_key():
    """Generate a Fernet encryption key"""
    return Fernet.generate_key().decode()

def generate_jwt_secret(length=64):
    """Generate a strong JWT secret"""
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*()_+-=[]{}|;:,.<>?"
    return ''.join(secrets.choice(alphabet) for _ in range(length))

def generate_database_password(length=32):
    """Generate a secure database password"""
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))

def generate_redis_password(length=32):
    """Generate a secure Redis password"""
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))

def main():
    print("=" * 60)
    print("NEXA PRODUCTION SECRETS GENERATOR")
    print("=" * 60)
    print("\nCopy these values to your .env file:\n")
    
    # Generate encryption key
    encryption_key = generate_fernet_key()
    print(f"ENCRYPTION_KEY={encryption_key}")
    
    # Generate JWT secret
    jwt_secret = generate_jwt_secret()
    print(f"JWT_SECRET={jwt_secret}")
    
    # Generate database password
    db_password = generate_database_password()
    print(f"# Database password (update DATABASE_URL):")
    print(f"# Password: {db_password}")
    print(f"DATABASE_URL=postgresql://nexa:{db_password}@localhost:5432/nexa_db")
    
    # Generate Redis password
    redis_password = generate_redis_password()
    print(f"\n# Redis password (update REDIS_URL):")
    print(f"# Password: {redis_password}")
    print(f"REDIS_URL=redis://:{redis_password}@localhost:6379/0")
    
    # Generate API keys placeholders
    print("\n# External service keys (obtain from providers):")
    print("OPENAI_API_KEY=sk-...")
    print("ANTHROPIC_API_KEY=sk-ant-...")
    print("HUGGINGFACE_TOKEN=hf_...")
    print("ROBOFLOW_API_KEY=rf_...")
    
    print("\n" + "=" * 60)
    print("⚠️  IMPORTANT SECURITY NOTES:")
    print("=" * 60)
    print("1. NEVER commit these secrets to version control")
    print("2. Store .env file securely with restricted permissions")
    print("3. Use different secrets for each environment")
    print("4. Rotate secrets regularly (every 90 days)")
    print("5. Use a secrets manager in production (AWS Secrets Manager, etc.)")
    
    print("\n✅ Secrets generated successfully!")
    
    # Optionally save to a secure file
    save = input("\nSave to 'secrets.txt' file? (y/n): ").lower()
    if save == 'y':
        with open('secrets.txt', 'w') as f:
            f.write(f"ENCRYPTION_KEY={encryption_key}\n")
            f.write(f"JWT_SECRET={jwt_secret}\n")
            f.write(f"DATABASE_URL=postgresql://nexa:{db_password}@localhost:5432/nexa_db\n")
            f.write(f"REDIS_URL=redis://:{redis_password}@localhost:6379/0\n")
        
        # Set restrictive permissions on Unix-like systems
        try:
            os.chmod('secrets.txt', 0o600)
            print("✅ Saved to 'secrets.txt' with restricted permissions (600)")
        except:
            print("✅ Saved to 'secrets.txt' (set file permissions manually)")
        
        print("⚠️  Remember to delete 'secrets.txt' after copying to .env!")

if __name__ == "__main__":
    main()
