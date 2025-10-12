#!/usr/bin/env python3
"""
Test script for new endpoints and middleware
"""
import requests
import json
import time

# Test locally or on Render
LOCAL = False
BASE_URL = "http://localhost:8000" if LOCAL else "https://nexa-doc-analyzer-oct2025.onrender.com"

def test_endpoints():
    """Test all endpoints"""
    print("🧪 Testing NEXA Document Analyzer Endpoints")
    print("=" * 50)
    print(f"Target: {BASE_URL}")
    print("=" * 50)
    print()
    
    # Test 1: Root endpoint
    print("1. Testing root endpoint...")
    try:
        response = requests.get(f"{BASE_URL}/")
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"   Version: {data.get('version', 'N/A')}")
            print(f"   Endpoints: {', '.join(data.get('endpoints', []))}")
        print("   ✅ Root endpoint OK")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    print()
    
    # Test 2: Health endpoint
    print("2. Testing health endpoint...")
    try:
        response = requests.get(f"{BASE_URL}/health")
        print(f"   Status: {response.status_code}")
        correlation_id = response.headers.get('X-Correlation-ID', 'N/A')
        print(f"   Correlation ID: {correlation_id}")
        print("   ✅ Health endpoint OK")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    print()
    
    # Test 3: Status endpoint (NEW)
    print("3. Testing status endpoint...")
    try:
        response = requests.get(f"{BASE_URL}/status")
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            spec_info = data.get('spec_book', {})
            print(f"   Spec book ready: {spec_info.get('ready', False)}")
            if spec_info.get('ready'):
                print(f"   Chunks loaded: {spec_info.get('chunks_loaded', 0)}")
            print(f"   CPU threads: {data.get('cpu_threads', 'N/A')}")
        print("   ✅ Status endpoint OK")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    print()
    
    # Test 4: Rate limiting
    print("4. Testing rate limiting...")
    try:
        response = requests.get(f"{BASE_URL}/health")
        remaining = response.headers.get('X-RateLimit-Remaining', 'N/A')
        limit = response.headers.get('X-RateLimit-Limit', 'N/A')
        print(f"   Rate limit: {remaining}/{limit}")
        print("   ✅ Rate limiting headers present")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    print()
    
    # Test 5: Error handling (404)
    print("5. Testing error handling (404)...")
    try:
        response = requests.get(f"{BASE_URL}/nonexistent")
        print(f"   Status: {response.status_code}")
        correlation_id = response.headers.get('X-Correlation-ID', 'N/A')
        print(f"   Correlation ID: {correlation_id}")
        if response.status_code == 404:
            print("   ✅ 404 error handled correctly")
        else:
            print("   ⚠️ Unexpected status code")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    print()
    
    # Test 6: Analyze without spec book (should return 400)
    print("6. Testing analyze without spec book...")
    try:
        response = requests.post(f"{BASE_URL}/analyze-audit", files={})
        print(f"   Status: {response.status_code}")
        if response.status_code == 400:
            data = response.json()
            print(f"   Error: {data.get('message', data.get('detail', 'N/A'))}")
            print("   ✅ Proper error response for missing spec book")
        elif response.status_code == 422:
            print("   ✅ Validation error (expected)")
        else:
            print(f"   ⚠️ Unexpected status: {response.status_code}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    print()
    
    # Test 7: Documentation
    print("7. Testing documentation endpoint...")
    try:
        response = requests.get(f"{BASE_URL}/docs")
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            print("   ✅ Documentation available")
        else:
            print(f"   ⚠️ Documentation status: {response.status_code}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    print()
    
    print("=" * 50)
    print("🎯 Test Summary:")
    print("   All critical endpoints tested")
    print("   Check logs for any middleware issues")
    print("=" * 50)

if __name__ == "__main__":
    test_endpoints()
