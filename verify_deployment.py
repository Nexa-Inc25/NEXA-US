#!/usr/bin/env python3
"""
Verify which app is running on Render
"""
import requests
import json
import sys

def check_deployment():
    """Check what's actually running"""
    
    urls = [
        "https://nexa-api.onrender.com",
        "https://nexa-doc-analyzer-oct2025.onrender.com"
    ]
    
    print("=" * 60)
    print("🔍 NEXA Deployment Verification")
    print("=" * 60)
    print()
    
    for base_url in urls:
        print(f"Checking: {base_url}")
        print("-" * 40)
        
        # Check for Streamlit (wrong)
        try:
            response = requests.get(base_url, timeout=10)
            if "streamlit" in response.text.lower() or "stlite" in response.text.lower():
                print("❌ WRONG: Streamlit is running!")
                print("   This should be FastAPI/uvicorn")
                continue
        except:
            pass
        
        # Check for FastAPI (correct)
        try:
            # Try health endpoint
            health_url = f"{base_url}/health"
            response = requests.get(health_url, timeout=10)
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    print("✅ CORRECT: FastAPI is running!")
                    print(f"   Health status: {data}")
                except:
                    print("✅ API responding (non-JSON)")
            else:
                print(f"⚠️ Health endpoint returned: {response.status_code}")
        except requests.exceptions.ConnectionError:
            print("❌ Service not responding")
        except requests.exceptions.Timeout:
            print("⏱️ Service timeout")
        except Exception as e:
            print(f"❌ Error: {e}")
        
        # Try docs endpoint
        try:
            docs_url = f"{base_url}/docs"
            response = requests.get(docs_url, timeout=5)
            if response.status_code == 200:
                if "swagger" in response.text.lower() or "fastapi" in response.text.lower():
                    print("✅ FastAPI docs available at /docs")
        except:
            pass
        
        print()
    
    print("=" * 60)
    print("\n📋 Summary:")
    print("If you see Streamlit → Dockerfile fix hasn't deployed yet")
    print("If you see FastAPI → Fix is working correctly")
    print("\n🚀 To deploy the fix:")
    print("1. Go to https://dashboard.render.com")
    print("2. Find 'nexa-api' service")
    print("3. Click 'Manual Deploy' → 'Deploy latest commit'")
    print("=" * 60)

if __name__ == "__main__":
    check_deployment()
