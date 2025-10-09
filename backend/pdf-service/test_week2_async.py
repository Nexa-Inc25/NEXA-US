"""
Test Suite for Week 2 Async Implementation
Tests Redis caching, Celery worker, and async endpoints
"""
import requests
import time
import json
from pathlib import Path

# Configuration
BASE_URL = "https://nexa-api-xpu3.onrender.com"
LOCAL_URL = "http://localhost:8000"  # For local testing

# Use production URL
API_URL = BASE_URL

def test_health_check():
    """Test basic API health"""
    print("🔍 Testing API Health...")
    response = requests.get(f"{API_URL}/health")
    assert response.status_code == 200
    data = response.json()
    print(f"✅ Health Check: {data}")
    return True

def test_queue_status():
    """Test Celery worker status"""
    print("\n🔍 Testing Queue Status...")
    response = requests.get(f"{API_URL}/queue-status")
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Queue Status: {json.dumps(data, indent=2)}")
        assert data.get("workers", {}).get("available") == True
        return True
    else:
        print(f"⚠️ Queue endpoint not yet implemented: {response.status_code}")
        return False

def test_cache_stats():
    """Test Redis cache statistics"""
    print("\n🔍 Testing Cache Stats...")
    response = requests.get(f"{API_URL}/cache-stats")
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Cache Stats: {json.dumps(data, indent=2)}")
        return True
    else:
        print(f"⚠️ Cache stats endpoint not yet implemented: {response.status_code}")
        return False

def test_async_upload(pdf_path=None):
    """Test async PDF upload and processing"""
    print("\n🔍 Testing Async Upload...")
    
    # Create a test PDF if none provided
    if not pdf_path:
        # Use a simple test file
        test_content = b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nendobj\nxref\n0 2\ntrailer\n<< /Size 2 >>\nstartxref\n9\n%%EOF"
        with open("test_audit.pdf", "wb") as f:
            f.write(test_content)
        pdf_path = "test_audit.pdf"
    
    # Submit async job
    with open(pdf_path, "rb") as f:
        files = {"file": ("test_audit.pdf", f, "application/pdf")}
        response = requests.post(f"{API_URL}/analyze-audit-async", files=files)
    
    if response.status_code == 200:
        data = response.json()
        job_id = data.get("job_id")
        print(f"✅ Job submitted: {job_id}")
        print(f"   Status: {data.get('status')}")
        
        # Poll for results
        print("\n⏳ Polling for results...")
        for i in range(30):  # Poll for up to 30 seconds
            time.sleep(1)
            result_response = requests.get(f"{API_URL}/job-result/{job_id}")
            if result_response.status_code == 200:
                result = result_response.json()
                status = result.get("status")
                print(f"   Status: {status}")
                if status == "SUCCESS":
                    print(f"✅ Job completed successfully!")
                    print(f"   Result: {json.dumps(result.get('result', {}), indent=2)[:200]}...")
                    return True
                elif status == "FAILURE":
                    print(f"❌ Job failed: {result.get('error')}")
                    return False
        
        print("⏱️ Job still processing after 30 seconds")
        return False
    else:
        print(f"⚠️ Async endpoint not yet implemented: {response.status_code}")
        print(f"   Response: {response.text[:200]}")
        return False

def test_batch_analyze():
    """Test batch processing capability"""
    print("\n🔍 Testing Batch Analysis...")
    
    # Create multiple test files
    test_files = []
    for i in range(3):
        content = f"%PDF-1.4\nTest PDF {i+1}\n%%EOF".encode()
        filename = f"test_batch_{i+1}.pdf"
        with open(filename, "wb") as f:
            f.write(content)
        test_files.append(filename)
    
    # Submit batch
    files = []
    for filename in test_files:
        with open(filename, "rb") as f:
            files.append(("files", (filename, f.read(), "application/pdf")))
    
    response = requests.post(f"{API_URL}/batch-analyze", files=files)
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Batch submitted: {len(data.get('job_ids', []))} jobs")
        return True
    else:
        print(f"⚠️ Batch endpoint not yet implemented: {response.status_code}")
        return False

def test_spec_library():
    """Test spec library status"""
    print("\n🔍 Testing Spec Library...")
    response = requests.get(f"{API_URL}/spec-library")
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Spec Library:")
        print(f"   Total specs: {data.get('total_specs', 0)}")
        print(f"   Categories: {len(data.get('categories', {}))}")
        return True
    else:
        print(f"❌ Spec library error: {response.status_code}")
        return False

def run_all_tests():
    """Run complete test suite"""
    print("=" * 50)
    print("🚀 NEXA Week 2 Async System Test Suite")
    print("=" * 50)
    
    results = {
        "Health Check": test_health_check(),
        "Spec Library": test_spec_library(),
        "Queue Status": test_queue_status(),
        "Cache Stats": test_cache_stats(),
        "Async Upload": test_async_upload(),
        "Batch Analysis": test_batch_analyze(),
    }
    
    print("\n" + "=" * 50)
    print("📊 TEST RESULTS SUMMARY")
    print("=" * 50)
    
    for test_name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL" if passed is False else "⚠️ NOT IMPLEMENTED"
        print(f"{test_name:.<30} {status}")
    
    total = len(results)
    passed = sum(1 for v in results.values() if v == True)
    failed = sum(1 for v in results.values() if v == False)
    not_impl = total - passed - failed
    
    print("\n" + "=" * 50)
    print(f"Total: {total} | Passed: {passed} | Failed: {failed} | Not Implemented: {not_impl}")
    print("=" * 50)
    
    if not_impl > 0:
        print("\n⚠️ Some endpoints need implementation in app_oct2025_enhanced.py")
        print("Run this test again after implementing missing endpoints.")

if __name__ == "__main__":
    run_all_tests()
