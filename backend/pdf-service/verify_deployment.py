#!/usr/bin/env python3
"""
Deployment Verification Script
Checks which app configuration should be used
"""

import os
import sys

def check_deployment():
    print("🔍 NEXA Document Analyzer - Deployment Checker")
    print("=" * 50)
    
    # Check for database configuration
    db_url = os.getenv("DATABASE_URL")
    if db_url:
        print("✅ DATABASE_URL found")
        print(f"   Value: {db_url[:30]}...")
        print("   → Recommendation: Use api.py (PostgreSQL version)")
    else:
        print("❌ DATABASE_URL not found")
        print("   → Recommendation: Use app_oct2025_enhanced.py (local storage)")
    
    print("\n" + "-" * 50)
    print("📁 Checking for required files:")
    
    files_to_check = {
        "app_oct2025_enhanced.py": "October 2025 version (local storage)",
        "api.py": "Original version (PostgreSQL required)",
        "Dockerfile.oct2025": "Docker configuration for Oct 2025",
        "requirements_oct2025.txt": "Dependencies for Oct 2025"
    }
    
    for filename, description in files_to_check.items():
        if os.path.exists(filename):
            print(f"✅ {filename}")
            print(f"   {description}")
        else:
            print(f"❌ {filename} - NOT FOUND")
    
    print("\n" + "-" * 50)
    print("📊 Checking dependencies:")
    
    try:
        import psycopg2
        print("✅ psycopg2 installed - PostgreSQL support available")
    except ImportError:
        print("❌ psycopg2 NOT installed - Cannot use PostgreSQL")
    
    try:
        from sentence_transformers import SentenceTransformer
        print("✅ sentence-transformers installed")
    except ImportError:
        print("❌ sentence-transformers NOT installed")
    
    print("\n" + "=" * 50)
    print("🎯 DEPLOYMENT RECOMMENDATION:")
    print("-" * 50)
    
    if not db_url:
        print("Use: app_oct2025_enhanced.py")
        print("Start command: uvicorn app_oct2025_enhanced:app --host 0.0.0.0 --port 8000")
        print("\nThis version uses local file storage at /data/")
        print("Perfect for Render's persistent disk storage")
    else:
        print("Use: api.py (if you want PostgreSQL)")
        print("Start command: uvicorn api:app --host 0.0.0.0 --port 8000")
        print("\nMake sure psycopg2-binary is in requirements.txt")
    
    print("\n" + "=" * 50)

if __name__ == "__main__":
    check_deployment()
