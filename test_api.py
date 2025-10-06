#!/usr/bin/env python3
"""Test script for NEXA AI Document Analyzer API"""

import requests
import time

# Update this to your Render URL
BASE_URL = "https://nexa-ai-analyzer-python.onrender.com"

def test_api():
    """Test the API endpoints"""
    
    print(f"Testing NEXA API at {BASE_URL}")
    print("-" * 50)
    
    # Test health endpoint
    print("\n1. Testing /health endpoint...")
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=10)
        if response.status_code == 200:
            print(f"✅ Health check passed: {response.json()}")
        else:
            print(f"❌ Health check failed: Status {response.status_code}")
    except requests.exceptions.RequestException as e:
        print(f"❌ Connection error: {e}")
        return
    
    # Test API docs
    print("\n2. Testing /docs endpoint...")
    try:
        response = requests.get(f"{BASE_URL}/docs", timeout=10)
        if response.status_code == 200:
            print("✅ API docs accessible")
        else:
            print(f"❌ API docs not accessible: Status {response.status_code}")
    except requests.exceptions.RequestException as e:
        print(f"❌ Error accessing docs: {e}")
    
    # Test analyzer health
    print("\n3. Testing /analyzer/health endpoint...")
    try:
        response = requests.get(f"{BASE_URL}/analyzer/health", timeout=10)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Analyzer status: {data}")
        else:
            print(f"❌ Analyzer health check failed: Status {response.status_code}")
    except requests.exceptions.RequestException as e:
        print(f"❌ Error checking analyzer: {e}")
    
    print("\n" + "=" * 50)
    print("API Test Complete!")

if __name__ == "__main__":
    test_api()
