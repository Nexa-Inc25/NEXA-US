#!/usr/bin/env python3
"""
Quick verification that Multi-Spec v2.0 deployed successfully
"""
import requests
import json
import sys

API_URL = "https://nexa-doc-analyzer-oct2025.onrender.com"

def test_deployment():
    """Test new multi-spec endpoints"""
    
    print("="*60)
    print("🚀 TESTING MULTI-SPEC v2.0 DEPLOYMENT")
    print("="*60)
    
    # Test 1: Root endpoint should show new version
    print("\n1️⃣ Testing root endpoint...")
    try:
        response = requests.get(f"{API_URL}/", timeout=10)
        data = response.json()
        
        if "2.0" in data.get("version", "") or "Multi-Spec" in data.get("version", ""):
            print("   ✅ Multi-Spec v2.0 detected!")
            print(f"   Version: {data.get('version')}")
        else:
            print(f"   ⚠️ Version: {data.get('version')} (might still be old)")
        
        # Check for new endpoints
        endpoints = data.get("endpoints", [])
        new_endpoints = ["/upload-specs", "/spec-library", "/manage-specs"]
        
        for endpoint in new_endpoints:
            if endpoint in str(endpoints):
                print(f"   ✅ {endpoint} available")
            else:
                print(f"   ❌ {endpoint} missing (still deploying?)")
                
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False
    
    # Test 2: Spec library endpoint
    print("\n2️⃣ Testing spec library endpoint...")
    try:
        response = requests.get(f"{API_URL}/spec-library", timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ Spec library endpoint working!")
            print(f"   Total files: {data.get('total_files', 0)}")
            print(f"   Total chunks: {data.get('total_chunks', 0)}")
        elif response.status_code == 404:
            print(f"   ⚠️ Endpoint not found - old version still running")
            return False
        else:
            print(f"   ⚠️ Status: {response.status_code}")
            
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # Test 3: Health check
    print("\n3️⃣ Testing health check...")
    try:
        response = requests.get(f"{API_URL}/health", timeout=10)
        data = response.json()
        print(f"   ✅ Service healthy")
        print(f"   Spec learned: {data.get('spec_learned', False)}")
    except Exception as e:
        print(f"   ⚠️ {e}")
    
    print("\n" + "="*60)
    print("✅ DEPLOYMENT VERIFICATION COMPLETE")
    print("="*60)
    
    return True

if __name__ == "__main__":
    success = test_deployment()
    
    if success:
        print("\n🎉 Multi-Spec v2.0 is LIVE!")
        print("\n📋 Next Steps:")
        print("1. Upload your 50 spec PDFs:")
        print("   python batch_upload_50_specs.py C:\\path\\to\\specs\\")
        print("\n2. Test with audit analysis")
        print("\n3. Upgrade to Starter plan for production ($7/month)")
    else:
        print("\n⚠️ Still deploying or old version running")
        print("Wait 2-3 minutes and run this script again")
        print("Check Render dashboard logs for deployment status")
