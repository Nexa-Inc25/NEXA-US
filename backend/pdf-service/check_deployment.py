"""
Quick deployment status checker for NEXA services
"""
import requests
import json
import time

BASE_URL = "https://nexa-api-xpu3.onrender.com"

def check_services():
    """Check all services are responding"""
    print("🔍 Checking NEXA Service Status...")
    print("=" * 50)
    
    # 1. Basic health
    try:
        resp = requests.get(f"{BASE_URL}/health", timeout=5)
        print(f"✅ API Health: {resp.status_code}")
    except:
        print(f"❌ API Health: Not responding")
    
    # 2. Queue status (new endpoint)
    try:
        resp = requests.get(f"{BASE_URL}/queue-status", timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            workers = data.get('workers', {})
            if workers.get('available'):
                print(f"✅ Celery Workers: {workers.get('count', 0)} active")
            else:
                print(f"⚠️ Celery Workers: No workers available")
        else:
            print(f"⚠️ Queue Status: {resp.status_code} - Endpoint deploying...")
    except Exception as e:
        print(f"⚠️ Queue Status: Not ready - {str(e)[:30]}")
    
    # 3. Cache stats (new endpoint)
    try:
        resp = requests.get(f"{BASE_URL}/cache-stats", timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            if data.get('status') == 'active':
                print(f"✅ Redis Cache: Active - {data.get('memory', {}).get('used_memory', 'N/A')}")
            else:
                print(f"⚠️ Redis Cache: {data.get('status', 'unknown')}")
        else:
            print(f"⚠️ Cache Stats: {resp.status_code} - Endpoint deploying...")
    except:
        print(f"⚠️ Cache Stats: Not ready")
    
    # 4. Async endpoint check
    try:
        # Try to submit a tiny test job
        test_pdf = b"%PDF-1.4\nTest\n%%EOF"
        files = {"file": ("test.pdf", test_pdf, "application/pdf")}
        resp = requests.post(f"{BASE_URL}/analyze-audit-async", files=files, timeout=5)
        if resp.status_code == 200:
            job_id = resp.json().get('job_id')
            print(f"✅ Async Endpoint: Working (job_id: {job_id[:8]}...)")
        else:
            print(f"⚠️ Async Endpoint: {resp.status_code} - Deploying...")
    except:
        print(f"⚠️ Async Endpoint: Not ready")
    
    print("=" * 50)

if __name__ == "__main__":
    check_services()
    
    print("\nWaiting for full deployment...")
    print("This typically takes 2-3 minutes after push")
    print("\nPress Ctrl+C to stop monitoring\n")
    
    # Monitor every 30 seconds
    try:
        while True:
            time.sleep(30)
            print(f"\n🔄 Status at {time.strftime('%H:%M:%S')}:")
            check_services()
    except KeyboardInterrupt:
        print("\n✋ Monitoring stopped")
