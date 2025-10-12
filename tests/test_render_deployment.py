"""
Test script for NEXA AI Document Analyzer on Render
"""
import requests
import time

# Replace with your actual Render URL
BASE_URL = "https://nexa-ui.onrender.com"  # or your service URL

def test_streamlit_ui():
    """Test if Streamlit UI is accessible"""
    print("Testing Streamlit UI...")
    try:
        response = requests.get(BASE_URL, timeout=10)
        if response.status_code == 200:
            if "streamlit" in response.text.lower() or "stApp" in response.text:
                print(f"✅ Streamlit UI is running at {BASE_URL}")
                print(f"   Open in browser: {BASE_URL}")
                return True
            else:
                print(f"⚠️ Page loaded but doesn't appear to be Streamlit")
        else:
            print(f"❌ Failed with status code: {response.status_code}")
    except Exception as e:
        print(f"❌ Error: {str(e)}")
    return False

def test_fastapi_health():
    """Test FastAPI health endpoint (if using API)"""
    print("\nTesting FastAPI health endpoint...")
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=10)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ API Health Check Passed")
            print(f"   Status: {data.get('status', 'unknown')}")
            return True
        else:
            print(f"❌ Health check failed: {response.status_code}")
    except Exception as e:
        print(f"ℹ️ No API health endpoint (might be using Streamlit UI)")
    return False

def test_api_docs():
    """Test FastAPI documentation (if using API)"""
    print("\nTesting API documentation...")
    try:
        response = requests.get(f"{BASE_URL}/docs", timeout=10)
        if response.status_code == 200:
            print(f"✅ API Documentation available at {BASE_URL}/docs")
            return True
    except:
        print(f"ℹ️ No API docs (might be using Streamlit UI)")
    return False

if __name__ == "__main__":
    print("=" * 60)
    print("NEXA AI Document Analyzer - Render Deployment Test")
    print("=" * 60)
    print(f"Testing URL: {BASE_URL}")
    print("-" * 60)
    
    # Wait a moment for service to be ready
    print("Waiting for service to respond...")
    time.sleep(2)
    
    # Run tests
    ui_ok = test_streamlit_ui()
    api_ok = test_fastapi_health()
    docs_ok = test_api_docs()
    
    print("\n" + "=" * 60)
    if ui_ok:
        print("✅ DEPLOYMENT SUCCESSFUL - Streamlit UI is live!")
        print(f"📊 Access your NEXA Document Analyzer at: {BASE_URL}")
    elif api_ok:
        print("✅ DEPLOYMENT SUCCESSFUL - FastAPI is live!")
        print(f"📊 API Documentation: {BASE_URL}/docs")
    else:
        print("⚠️ Service may still be starting. Check Render logs.")
    print("=" * 60)
