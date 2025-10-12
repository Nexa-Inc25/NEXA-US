"""
Universal Standards Engine Test Suite - FIXED VERSION
Tests all endpoints with correct request formats
"""
import os
import requests
import json
from typing import Optional

# Test configuration
BASE_URL = os.getenv('TEST_URL', 'http://localhost:8000')
AUTH_TOKEN = None

def test_health():
    """Test health endpoint"""
    print("🏥 Testing Health Check...")
    response = requests.get(f"{BASE_URL}/health")
    if response.status_code == 200:
        print(f"  ✅ PASS: Server healthy - {response.json()['status']}")
        return True
    else:
        print(f"  ❌ FAIL: Health check failed - {response.status_code}")
        return False

def test_auth():
    """Test authentication"""
    global AUTH_TOKEN
    print("\n🔐 Testing Authentication...")
    
    # Try to login with default admin credentials
    payload = {
        "email": "admin@nexa.com",
        "password": "admin123"
    }
    
    response = requests.post(f"{BASE_URL}/auth/login", json=payload)
    
    if response.status_code == 200:
        data = response.json()
        AUTH_TOKEN = data.get('access_token')
        print(f"  ✅ PASS: Authenticated as {data.get('user', {}).get('email', 'unknown')}")
        return True
    elif response.status_code == 404:
        print(f"  ⚠️ Auth not available (404)")
        return False
    else:
        print(f"  ❌ FAIL: Auth failed - {response.status_code}")
        print(f"     Response: {response.text[:200]}")
        return False

def get_headers():
    """Get headers with auth token if available"""
    headers = {"Content-Type": "application/json"}
    if AUTH_TOKEN:
        headers["Authorization"] = f"Bearer {AUTH_TOKEN}"
    return headers

def test_utility_detection():
    """Test GPS utility detection with CORRECT format"""
    print("\n🗺️ Testing Utility Detection...")
    
    # Test cases with CORRECT nested format
    test_cases = [
        (37.7749, -122.4194, "PGE"),  # San Francisco
        (25.7617, -80.1918, "FPL"),    # Miami
        (40.7128, -74.0060, None)       # New York (no utility)
    ]
    
    passed = True
    for lat, lng, expected in test_cases:
        # CORRECT FORMAT: Nested location object
        payload = {
            "location": {
                "lat": lat,
                "lng": lng
            }
        }
        
        response = requests.post(
            f"{BASE_URL}/api/utilities/detect",
            json=payload,
            headers=get_headers()
        )
        
        if response.status_code == 200:
            data = response.json()
            utility = data.get('utility_id')
            if expected and utility == expected:
                print(f"  ✅ PASS: Detected {utility} at ({lat}, {lng})")
            elif not expected and not utility:
                print(f"  ✅ PASS: No utility at ({lat}, {lng})")
            else:
                print(f"  ❌ FAIL: Expected {expected}, got {utility}")
                passed = False
        else:
            print(f"  ❌ FAIL: Status {response.status_code}: {response.text[:100]}")
            passed = False
    
    return passed

def test_utility_list():
    """Test listing all utilities"""
    print("\n📋 Testing Utility List...")
    
    response = requests.get(
        f"{BASE_URL}/api/utilities/list",
        headers=get_headers()
    )
    
    if response.status_code == 200:
        data = response.json()
        utilities = data.get('utilities', [])
        utility_ids = [u['id'] for u in utilities]
        print(f"  ✅ PASS: Found {len(utilities)} utilities: {', '.join(utility_ids)}")
        return True
    else:
        print(f"  ❌ FAIL: Status {response.status_code}")
        return False

def test_spec_ingestion():
    """Test spec ingestion with mock PDF"""
    print("\n📄 Testing Spec Ingestion...")
    
    # Create a minimal mock PDF
    pdf_content = b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
    pdf_content += b"2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n"
    pdf_content += b"3 0 obj<</Type/Page/MediaBox[0 0 612 792]/Parent 2 0 R/Resources<<>>>>endobj\n"
    pdf_content += b"xref\n0 4\n0000000000 65535 f\n0000000009 00000 n\n"
    pdf_content += b"0000000058 00000 n\n0000000115 00000 n\ntrailer<</Size 4/Root 1 0 R>>\n"
    pdf_content += b"startxref\n203\n%%EOF"
    
    headers = {}
    if AUTH_TOKEN:
        headers["Authorization"] = f"Bearer {AUTH_TOKEN}"
    
    files = {'file': ('test_spec.pdf', pdf_content, 'application/pdf')}
    response = requests.post(
        f"{BASE_URL}/api/utilities/PGE/ingest",
        files=files,
        headers=headers
    )
    
    if response.status_code == 200:
        data = response.json()
        print(f"  ✅ PASS: Ingested spec for PGE")
        return True
    else:
        print(f"  ❌ FAIL: Status {response.status_code}: {response.text[:100]}")
        return False

def test_cross_reference():
    """Test cross-reference with CORRECT format"""
    print("\n🔄 Testing Cross-Reference...")
    
    # CORRECT FORMAT: Nested request object
    payload = {
        "request": {
            "requirement": "capacitor spacing"
        }
    }
    
    response = requests.post(
        f"{BASE_URL}/api/utilities/standards/cross-reference",
        json=payload,
        headers=get_headers()
    )
    
    if response.status_code == 200:
        data = response.json()
        utilities = data.get('utilities_compared', 0)
        print(f"  ✅ PASS: Cross-referenced across {utilities} utilities")
        return True
    else:
        print(f"  ❌ FAIL: Status {response.status_code}: {response.text[:100]}")
        return False

def test_job_creation():
    """Test job creation with CORRECT format"""
    print("\n💼 Testing Job Creation...")
    
    # CORRECT FORMAT: Nested request object
    payload = {
        "request": {
            "pm_number": "PM-2025-TEST",
            "description": "Test job for Universal Standards",
            "lat": 37.7749,
            "lng": -122.4194
        }
    }
    
    response = requests.post(
        f"{BASE_URL}/api/utilities/jobs/create",
        json=payload,
        headers=get_headers()
    )
    
    if response.status_code == 200:
        data = response.json()
        job = data.get('job', {})
        print(f"  ✅ PASS: Created job {job.get('pm_number')} for {job.get('utility_name')}")
        return True
    else:
        print(f"  ❌ FAIL: Status {response.status_code}: {response.text[:100]}")
        return False

def test_form_population():
    """Test form population with CORRECT format"""
    print("\n📝 Testing Form Population...")
    
    # CORRECT FORMAT: Nested request object
    payload = {
        "request": {
            "universal_data": {
                "job_id": "TEST-001",
                "pm_number": "PM-2025-001",
                "location": "San Francisco",
                "equipment": ["Capacitor", "Pole"],
                "clearances": {"overhead": "18 feet", "underground": "36 inches"}
            }
        }
    }
    
    response = requests.post(
        f"{BASE_URL}/api/utilities/forms/PGE/populate",
        json=payload,
        headers=get_headers()
    )
    
    if response.status_code == 200:
        data = response.json()
        print(f"  ✅ PASS: Populated form for PGE")
        return True
    else:
        print(f"  ❌ FAIL: Status {response.status_code}: {response.text[:100]}")
        return False

def test_audit_analysis():
    """Test audit analysis"""
    print("\n🔍 Testing Audit Analysis...")
    
    # Create a minimal mock PDF for audit
    pdf_content = b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
    pdf_content += b"2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n"
    pdf_content += b"3 0 obj<</Type/Page/MediaBox[0 0 612 792]/Parent 2 0 R/Resources<<>>>>endobj\n"
    pdf_content += b"xref\n0 4\n0000000000 65535 f\n0000000009 00000 n\n"
    pdf_content += b"0000000058 00000 n\n0000000115 00000 n\ntrailer<</Size 4/Root 1 0 R>>\n"
    pdf_content += b"startxref\n203\n%%EOF"
    
    headers = {}
    if AUTH_TOKEN:
        headers["Authorization"] = f"Bearer {AUTH_TOKEN}"
    
    files = {'file': ('test_audit.pdf', pdf_content, 'application/pdf')}
    response = requests.post(
        f"{BASE_URL}/analyze-audit",
        files=files,
        headers=headers
    )
    
    if response.status_code == 200:
        data = response.json()
        print(f"  ✅ PASS: Analyzed audit, found {len(data.get('infractions', []))} infractions")
        return True
    elif response.status_code == 400:
        print(f"  ⚠️ No spec files in library (expected if not initialized)")
        return False
    else:
        print(f"  ❌ FAIL: Status {response.status_code}: {response.text[:100]}")
        return False

def main():
    """Run all tests"""
    import sys
    
    # Check if running in production mode
    if len(sys.argv) > 1 and sys.argv[1] == 'prod':
        global BASE_URL
        BASE_URL = 'https://nexa-us-pro.onrender.com'
        print(f"🌐 Testing PRODUCTION: {BASE_URL}")
    else:
        print(f"🏠 Testing LOCAL: {BASE_URL}")
    
    print("="*60)
    print("🚀 Universal Standards Engine Test Suite - FIXED")
    print("="*60)
    
    # Run tests
    results = []
    results.append(("Health Check", test_health()))
    results.append(("Authentication", test_auth()))
    results.append(("Utility Detection", test_utility_detection()))
    results.append(("Utility List", test_utility_list()))
    results.append(("Spec Ingestion", test_spec_ingestion()))
    results.append(("Cross-Reference", test_cross_reference()))
    results.append(("Job Creation", test_job_creation()))
    results.append(("Form Population", test_form_population()))
    results.append(("Audit Analysis", test_audit_analysis()))
    
    # Print summary
    print("\n" + "="*60)
    print("📊 TEST SUMMARY")
    print("="*60)
    
    passed_count = 0
    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {status}: {name}")
        if result:
            passed_count += 1
    
    total = len(results)
    percentage = (passed_count / total) * 100
    print(f"\n  Total: {passed_count}/{total} passed ({percentage:.0f}%)")
    
    if passed_count == total:
        print("\n🎉 All tests passed! Universal Standards Engine is fully operational!")
    else:
        print(f"\n⚠️ {total - passed_count} test(s) failed")
    
    print("="*60)
    
    return passed_count == total

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
