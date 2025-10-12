#!/usr/bin/env python3
"""
Check if the uvicorn fix was deployed successfully
"""
import requests
import time
import sys

def check_deployment():
    """Check if the API is responding after fix"""
    
    # Your API endpoints
    endpoints = [
        "https://nexa-api.onrender.com",  # Update with your actual URL
        "https://nexa-doc-analyzer-oct2025.onrender.com"
    ]
    
    print("🔍 Checking NEXA API Deployment Status...")
    print("=" * 50)
    print("\n📋 Fix Summary:")
    print("   - Added uvicorn[standard]==0.37.0 to requirements.txt")
    print("   - Added fastapi==0.118.0 to requirements.txt")
    print("   - Added python-multipart==0.0.20 to requirements.txt")
    print("\n" + "=" * 50)
    
    for url in endpoints:
        print(f"\n🌐 Checking {url}...")
        
        try:
            # Try health endpoint first
            health_url = f"{url}/health"
            response = requests.get(health_url, timeout=10)
            
            if response.status_code == 200:
                print(f"   ✅ API is LIVE and responding!")
                print(f"   Status Code: {response.status_code}")
                
                # Try to get more info
                try:
                    root_response = requests.get(url, timeout=5)
                    if root_response.status_code == 200:
                        data = root_response.json() if 'json' in root_response.headers.get('content-type', '') else {}
                        if data:
                            print(f"   Version: {data.get('version', 'N/A')}")
                            print(f"   Status: {data.get('status', 'N/A')}")
                except:
                    pass
                    
            else:
                print(f"   ⚠️ API responded but with status: {response.status_code}")
                
        except requests.exceptions.Timeout:
            print(f"   ⏱️ Timeout - API might still be starting up")
            print(f"   Try again in a few minutes")
            
        except requests.exceptions.ConnectionError:
            print(f"   ❌ Connection failed - API is not accessible")
            print(f"   Possible causes:")
            print(f"      1. Build still in progress")
            print(f"      2. Service crashed on startup")
            print(f"      3. Wrong URL")
            
        except Exception as e:
            print(f"   ❌ Error: {e}")
    
    print("\n" + "=" * 50)
    print("\n📝 Next Steps:")
    print("1. Check Render dashboard for build logs")
    print("2. Look for 'Successfully installed ... uvicorn' in logs")
    print("3. Verify service shows 'Live' status")
    print("4. If still failing, check the Dockerfile CMD line")
    print("\n✅ The fix has been committed to requirements.txt")
    print("📦 You may need to trigger a manual deploy on Render")

if __name__ == "__main__":
    check_deployment()
