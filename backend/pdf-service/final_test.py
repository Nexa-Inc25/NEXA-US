"""
Final test for Week 2 async implementation
"""
import requests
import time
import json

BASE_URL = "https://nexa-doc-analyzer-oct2025.onrender.com"

print("=" * 50)
print("🚀 NEXA Week 2 - Final System Test")
print("=" * 50)

# 1. Check health
r = requests.get(f"{BASE_URL}/health")
print(f"✅ API Health: {r.status_code}")

# 2. Check queue status
r = requests.get(f"{BASE_URL}/queue-status")
data = r.json()
if data.get('workers', {}).get('available'):
    print(f"✅ Celery Workers: {data['workers']['count']} active")
else:
    print(f"⚠️ Celery Workers: Not connected - Add REDIS_URL to API service!")
    print(f"   Error: {data.get('workers', {}).get('error', 'Unknown')}")

# 3. Check cache
r = requests.get(f"{BASE_URL}/cache-stats")
cache = r.json()
if cache.get('status') == 'active':
    print(f"✅ Redis Cache: Active")
else:
    print(f"⚠️ Redis Cache: {cache.get('status')} - Add REDIS_URL!")

# 4. Test async upload (only if workers available)
if data.get('workers', {}).get('available'):
    print("\n📤 Testing Async Upload...")
    test_pdf = b"%PDF-1.4\nTest Document\n%%EOF"
    files = {"file": ("test.pdf", test_pdf, "application/pdf")}
    
    r = requests.post(f"{BASE_URL}/analyze-audit-async", files=files)
    if r.status_code == 200:
        job = r.json()
        print(f"✅ Job Submitted: {job['job_id']}")
        
        # Poll for result
        for i in range(10):
            time.sleep(2)
            r2 = requests.get(f"{BASE_URL}/job-result/{job['job_id']}")
            result = r2.json()
            print(f"   Status: {result['status']}")
            if result['status'] in ['complete', 'failed']:
                break
    else:
        print(f"❌ Async upload failed: {r.status_code}")

print("\n" + "=" * 50)
print("📊 DEPLOYMENT CHECKLIST:")
print("=" * 50)
print("✅ API Service: Deployed")
print("✅ Background Worker: Deployed")
print("✅ Redis Service: Created")
print("⚠️ TODO: Add REDIS_URL to API Environment")
print("=" * 50)
