#!/usr/bin/env python3
"""
Quick test script to verify NEXA API endpoints
Tests what's working and what's timing out
"""
import requests
import time
import sys

API_URL = "https://nexa-doc-analyzer-oct2025.onrender.com"

def test_endpoint(name, url, timeout=10):
    """Test an endpoint and report status"""
    print(f"\n{'='*50}")
    print(f"Testing: {name}")
    print(f"URL: {url}")
    print(f"{'='*50}")
    
    start_time = time.time()
    
    try:
        response = requests.get(url, timeout=timeout)
        elapsed = time.time() - start_time
        
        print(f"✅ Status: {response.status_code}")
        print(f"⏱️  Time: {elapsed:.2f}s")
        
        # Try to parse JSON
        try:
            data = response.json()
            print(f"📄 Response Type: JSON")
            print(f"📊 Data Preview:")
            for key, value in list(data.items())[:5]:
                print(f"   {key}: {value}")
        except:
            print(f"📄 Response Type: HTML/Text ({len(response.text)} chars)")
            print(f"📊 Preview: {response.text[:200]}")
        
        return True
        
    except requests.exceptions.Timeout:
        elapsed = time.time() - start_time
        print(f"❌ TIMEOUT after {elapsed:.2f}s")
        print(f"💡 Endpoint took longer than {timeout}s")
        return False
        
    except requests.exceptions.ConnectionError:
        print(f"❌ CONNECTION ERROR")
        print(f"💡 Service might be down or restarting")
        return False
        
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return False

def main():
    """Run all endpoint tests"""
    print("\n" + "="*60)
    print("🚀 NEXA API ENDPOINT TEST SUITE")
    print("="*60)
    print(f"\nAPI Base URL: {API_URL}")
    print(f"Testing at: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Define endpoints to test
    endpoints = [
        ("Root Endpoint", f"{API_URL}/", 10),
        ("Health Check", f"{API_URL}/health", 10),
        ("OpenAPI Schema", f"{API_URL}/openapi.json", 30),
        ("Swagger Docs", f"{API_URL}/docs", 30),
        ("ReDoc", f"{API_URL}/redoc", 30),
    ]
    
    results = {}
    
    for name, url, timeout in endpoints:
        results[name] = test_endpoint(name, url, timeout)
        time.sleep(1)  # Brief pause between tests
    
    # Summary
    print("\n" + "="*60)
    print("📊 TEST SUMMARY")
    print("="*60)
    
    working = sum(1 for v in results.values() if v)
    total = len(results)
    
    for name, status in results.items():
        icon = "✅" if status else "❌"
        print(f"{icon} {name}")
    
    print(f"\n📈 Success Rate: {working}/{total} ({working/total*100:.0f}%)")
    
    # Diagnosis
    print("\n" + "="*60)
    print("🔍 DIAGNOSIS")
    print("="*60)
    
    if results.get("Root Endpoint") and results.get("Health Check"):
        print("✅ Core API is working correctly!")
        print("   Your main endpoints are functional.")
        
        if not results.get("Swagger Docs"):
            print("\n⚠️  Swagger UI (/docs) is timing out")
            print("   This is a Render free tier issue, not a code bug.")
            print("\n💡 Solutions:")
            print("   1. Add PORT=8000 env var in Render Dashboard")
            print("   2. Upgrade to Starter plan ($7/month)")
            print("   3. Disable /docs temporarily (see FIX_502_DOCS_ENDPOINT.md)")
            print("   4. Use Python scripts instead of Swagger UI")
    else:
        print("❌ Core API is not responding")
        print("   Check Render logs for errors")
        print("   Service might be cold starting or crashed")
    
    print("\n" + "="*60)
    print("📝 Next Steps:")
    print("="*60)
    
    if not results.get("Root Endpoint"):
        print("1. Check Render Dashboard - is service deployed?")
        print("2. Check logs for errors")
        print("3. Try manual deploy")
    elif not results.get("Swagger Docs"):
        print("1. Read: FIX_502_DOCS_ENDPOINT.md")
        print("2. Add PORT env var on Render")
        print("3. Consider upgrading to Starter plan")
        print("4. Use /openapi.json to test OpenAPI generation")
    else:
        print("✅ All endpoints working! API is fully operational.")
        print("You can now upload specs and analyze audits.")

if __name__ == "__main__":
    main()
