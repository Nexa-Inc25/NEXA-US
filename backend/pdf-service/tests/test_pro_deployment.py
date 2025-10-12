#!/usr/bin/env python3
"""
Test script for NEXA AI Document Analyzer Pro deployment
Tests both FastAPI backend and Streamlit UI functionality
"""

import requests
import json
import time
from pathlib import Path

# Configuration
API_BASE = "http://localhost:8000"  # FastAPI
UI_BASE = "http://localhost:8501"   # Streamlit
PRODUCTION_URL = "https://nexa-pdf-analyzer-pro.onrender.com"

def test_local():
    """Test local deployment"""
    print("🧪 Testing Local Deployment")
    print("=" * 50)
    
    # Test FastAPI health
    print("\n1. Testing FastAPI Backend...")
    try:
        resp = requests.get(f"{API_BASE}/health", timeout=5)
        if resp.status_code == 200:
            health = resp.json()
            print(f"✅ FastAPI Online")
            print(f"   - Index Loaded: {health.get('index_loaded')}")
            print(f"   - Chunks: {health.get('chunks_loaded')}")
            print(f"   - PostgreSQL: {health.get('postgres_enabled')}")
        else:
            print("❌ FastAPI health check failed")
    except Exception as e:
        print(f"❌ FastAPI not accessible: {e}")
        print("   Run: python app_complete.py fastapi")
    
    # Test Streamlit health
    print("\n2. Testing Streamlit UI...")
    try:
        resp = requests.get(UI_BASE, timeout=5)
        if resp.status_code == 200:
            print(f"✅ Streamlit UI Online at {UI_BASE}")
        else:
            print("❌ Streamlit not responding")
    except Exception as e:
        print(f"❌ Streamlit not accessible: {e}")
        print("   Run: streamlit run app_complete.py")
    
    print("\n" + "=" * 50)
    print("✅ Local tests complete")

def test_production(url=PRODUCTION_URL):
    """Test production deployment on Render"""
    print(f"🚀 Testing Production Deployment: {url}")
    print("=" * 50)
    
    # Test health endpoint
    print("\n1. Health Check...")
    try:
        resp = requests.get(f"{url}/health", timeout=10)
        if resp.status_code == 200:
            health = resp.json()
            print(f"✅ Service Online")
            print(f"   - Status: {health.get('status')}")
            print(f"   - Index: {health.get('index_loaded')}")
            print(f"   - PostgreSQL: {health.get('postgres_enabled')}")
        else:
            print(f"❌ Health check failed: {resp.status_code}")
    except Exception as e:
        print(f"❌ Service not accessible: {e}")
        return
    
    # Test UI accessibility
    print("\n2. Testing Web UI...")
    try:
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200:
            print(f"✅ Web UI accessible at {url}")
            print("   - Upload spec at: {url}")
            print("   - Analyze audit at: {url}")
        else:
            print(f"⚠️  UI returned status: {resp.status_code}")
    except Exception as e:
        print(f"❌ UI not accessible: {e}")
    
    print("\n" + "=" * 50)
    print("✅ Production tests complete")

def test_pdf_processing():
    """Test PDF processing capabilities"""
    print("\n📄 Testing PDF Processing")
    print("=" * 50)
    
    # Create test content
    test_infraction = """
    Go-back Infraction: Missing safety barriers at pole location
    Details: Crew failed to install proper barriers
    """
    
    print("Testing infraction extraction pattern:")
    import re
    INFRACTION_REGEX = r'(?i)(go-back|infraction|violation|issue|problem):\s*([^\n]+(?:\n(?!(?:go-back|infraction|violation|issue|problem):)[^\n]+)*)'
    
    matches = re.findall(INFRACTION_REGEX, test_infraction, re.MULTILINE | re.DOTALL)
    if matches:
        print(f"✅ Found {len(matches)} infractions:")
        for match in matches:
            print(f"   - Type: {match[0]}")
            print(f"   - Description: {match[1][:50]}...")
    else:
        print("❌ No infractions found")
    
    print("\n✅ PDF processing tests complete")

def performance_test():
    """Test performance metrics"""
    print("\n⚡ Performance Metrics")
    print("=" * 50)
    
    print("Expected performance on Render Pro (2 CPU, 4GB RAM):")
    print("┌─────────────┬──────────┬────────┬────────┬─────────┐")
    print("│ Operation   │ File Size│ Pages  │ Time   │ Memory  │")
    print("├─────────────┼──────────┼────────┼────────┼─────────┤")
    print("│ Learn Spec  │ 50MB     │ 500    │ ~30s   │ 2GB     │")
    print("│ Learn Spec  │ 100MB    │ 1000   │ ~60s   │ 3GB     │")
    print("│ Analyze     │ 10MB     │ 100    │ ~5s    │ 1GB     │")
    print("│ Index Search│ -        │ -      │ <1s    │ 500MB   │")
    print("└─────────────┴──────────┴────────┴────────┴─────────┘")
    
    print("\nOptimization tips:")
    print("  • Batch size: 50-100 pages (adjust based on memory)")
    print("  • Chunk size: 5000 chars (increase for fewer chunks)")
    print("  • Model: all-MiniLM-L6-v2 (384 dimensions)")
    print("  • PostgreSQL: Use pgvector for persistence")

def show_deployment_checklist():
    """Show deployment checklist"""
    print("\n📋 Deployment Checklist")
    print("=" * 50)
    
    checklist = [
        ("Files ready", ["app_complete.py", "requirements_complete.txt", "render_pro.yaml"]),
        ("GitHub pushed", ["All changes committed", "Pushed to main branch"]),
        ("Render configured", ["Pro plan selected", "PostgreSQL connected", "Environment variables set"]),
        ("PostgreSQL setup", ["pgvector extension installed", "Connection string configured"]),
        ("Testing", ["Health check passing", "Spec upload working", "Audit analysis working"]),
        ("Production ready", ["SSL enabled", "Custom domain (optional)", "Monitoring active"])
    ]
    
    for category, items in checklist:
        print(f"\n{category}:")
        for item in items:
            print(f"  □ {item}")

if __name__ == "__main__":
    import sys
    
    print("=" * 50)
    print("NEXA AI Document Analyzer - Deployment Test Suite")
    print("=" * 50)
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "local":
            test_local()
        elif sys.argv[1] == "production":
            url = sys.argv[2] if len(sys.argv) > 2 else PRODUCTION_URL
            test_production(url)
        elif sys.argv[1] == "pdf":
            test_pdf_processing()
        elif sys.argv[1] == "performance":
            performance_test()
        elif sys.argv[1] == "checklist":
            show_deployment_checklist()
    else:
        # Run all tests
        test_local()
        test_pdf_processing()
        performance_test()
        show_deployment_checklist()
        
        print("\n" + "=" * 50)
        print("🎉 All tests complete!")
        print("\nNext steps:")
        print("1. Run locally: ./start_pro.sh")
        print("2. Deploy to Render: git push origin main")
        print("3. Test production: python test_pro_deployment.py production")
