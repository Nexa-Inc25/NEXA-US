"""
Monitor deployment status
"""
import requests
import time
import sys

BASE_URL = "https://nexa-api-xpu3.onrender.com"

def check_ready():
    """Check if async endpoints are working"""
    try:
        # Check queue status
        r = requests.get(f"{BASE_URL}/queue-status", timeout=5)
        if r.status_code == 200:
            data = r.json()
            if data.get('workers', {}).get('available'):
                return True, "Workers Available!"
            elif "Celery not configured" in str(data):
                return False, "Celery not imported yet"
            else:
                return False, f"Workers not ready: {data}"
        else:
            return False, f"Queue endpoint: {r.status_code}"
    except Exception as e:
        return False, f"Error: {str(e)[:50]}"

print("🔍 Monitoring NEXA deployment...")
print("Waiting for Celery integration...")
print("-" * 50)

start_time = time.time()
last_status = ""

while True:
    ready, status = check_ready()
    
    if status != last_status:
        elapsed = int(time.time() - start_time)
        print(f"[{elapsed:3d}s] {status}")
        last_status = status
    
    if ready:
        print("\n✅ DEPLOYMENT SUCCESSFUL!")
        print("Celery workers are available!")
        
        # Test cache stats too
        r = requests.get(f"{BASE_URL}/cache-stats")
        if r.status_code == 200:
            cache = r.json()
            print(f"Redis status: {cache.get('status', 'unknown')}")
        
        break
    
    if time.time() - start_time > 600:  # 10 min timeout
        print("\n⏱️ Timeout - deployment taking too long")
        break
    
    time.sleep(10)  # Check every 10 seconds
