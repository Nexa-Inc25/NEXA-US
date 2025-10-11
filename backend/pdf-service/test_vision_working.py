#!/usr/bin/env python3
"""
Quick test to verify vision endpoints are working after PyTorch fix
"""
import requests
import json
import time

# Note: Your deployment logs show this URL
BASE_URL = "https://nexa-doc-analyzer-oct2025.onrender.com"

def quick_test():
    """Quick test of vision endpoints"""
    print("🔍 Testing Vision Endpoints")
    print("=" * 50)
    print(f"Service: {BASE_URL}")
    print(f"Time: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 50)
    
    # Test 1: Health check
    print("\n1. Health Check:")
    try:
        r = requests.get(f"{BASE_URL}/health", timeout=10)
        print(f"   Status: {r.status_code}")
        if r.status_code == 200:
            print("   ✅ Service is healthy")
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False
    
    # Test 2: Vision model status
    print("\n2. Vision Model Status:")
    try:
        r = requests.get(f"{BASE_URL}/vision/model-status", timeout=30)
        print(f"   Status: {r.status_code}")
        
        if r.status_code == 200:
            data = r.json()
            print("   ✅ Vision endpoints working!")
            print(f"   Response: {json.dumps(data, indent=4)}")
            
            if data.get('model_exists'):
                print("   ✅ Model is loaded and ready")
            else:
                print("   ⏳ Model will download on first use")
                
            return True
            
        elif r.status_code == 404:
            print("   ❌ Vision endpoints not found")
            print("   Check if vision files are deployed")
            return False
        else:
            print(f"   ⚠️ Unexpected: {r.text[:100]}")
            return False
            
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False

def main():
    success = quick_test()
    
    print("\n" + "=" * 50)
    if success:
        print("🎉 SUCCESS! Vision integration is working!")
        print("\nNext Steps:")
        print("1. Set ROBOFLOW_API_KEY in Render environment")
        print("2. Test with real pole images")
        print("3. Fine-tune on spec images")
    else:
        print("❌ Vision endpoints not working yet")
        print("\nTroubleshooting:")
        print("1. Wait for deployment to complete (3-5 min)")
        print("2. Check Render logs for errors")
        print("3. Verify PyTorch fix was deployed")
    print("=" * 50)
    
    return success

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
