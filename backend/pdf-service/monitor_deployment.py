#!/usr/bin/env python3
"""Monitor PyTorch fix deployment"""
import requests
import time
import json

print("🚀 Monitoring PyTorch Fix Deployment")
print("=" * 50)
print(f"Started at: {time.strftime('%H:%M:%S')}")
print("Will check every 30 seconds...")
print("=" * 50)

url = "https://nexa-doc-analyzer-oct2025.onrender.com/vision/model-status"
success = False
attempts = 0
max_attempts = 20  # 10 minutes max

while not success and attempts < max_attempts:
    attempts += 1
    print(f"\nAttempt {attempts} at {time.strftime('%H:%M:%S')}")
    
    try:
        r = requests.get(url, timeout=10)
        
        if r.status_code == 200:
            data = r.json()
            
            if data.get('status') == 'ready':
                print("🎉 SUCCESS! Vision model loaded!")
                print(json.dumps(data, indent=2))
                success = True
            elif 'error' in data and 'weights_only' in str(data['error']):
                print("⏳ Still deploying... (PyTorch not updated yet)")
            else:
                print(f"Status: {data.get('status', 'unknown')}")
        else:
            print(f"HTTP {r.status_code}")
            
    except Exception as e:
        print(f"Connection error (service may be restarting)")
    
    if not success and attempts < max_attempts:
        print("Waiting 30 seconds...")
        time.sleep(30)

if success:
    print("\n" + "=" * 50)
    print("✅ DEPLOYMENT SUCCESSFUL!")
    print("Vision integration is now working!")
    print("Roboflow model ready for pole detection")
    print("=" * 50)
else:
    print("\n" + "=" * 50)
    print("❌ Timeout - check Render logs")
    print("=" * 50)
