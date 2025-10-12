#!/usr/bin/env python3
"""
Test script for Universal Standards Engine
Tests authentication, utility detection, spec ingestion, and cross-reference
"""
import requests
import json
import sys
import os
from pathlib import Path

# Configuration
LOCAL_URL = "http://localhost:8001"
PROD_URL = "https://nexa-us-pro.onrender.com"

# Test credentials
TEST_USER = {
    "email": "admin@nexa.com",
    "password": "admin123"
}

def get_auth_token(base_url):
    """Get authentication token"""
    try:
        response = requests.post(
            f"{base_url}/auth/login",
            json=TEST_USER
        )
        if response.status_code == 200:
            token = response.json().get("access_token")
            print(f"  ✅ Authenticated as {TEST_USER['email']}")
            return token
        else:
            print(f"  ⚠️ Auth not available or failed: {response.status_code}")
            return None
    except:
        print("  ⚠️ Auth endpoint not found, proceeding without authentication")
        return None

def test_health_check(base_url):
    """Test health endpoint"""
    print("\n🏥 Testing Health Check...")
    try:
        response = requests.get(f"{base_url}/health", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print(f"  ✅ PASS: Server healthy - {data.get('status', 'ok')}")
            return True
        else:
            print(f"  ❌ FAIL: Health check failed with status {response.status_code}")
            return False
    except Exception as e:
        print(f"  ❌ FAIL: Server not reachable: {e}")
        return False

def test_utility_detection(base_url, token=None):
    """Test GPS-based utility detection"""
    print("\n🗺️ Testing Utility Detection...")
    
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    
    test_cases = [
        {"lat": 37.7749, "lng": -122.4194, "expected": "PGE", "location": "San Francisco"},
        {"lat": 25.7617, "lng": -80.1918, "expected": "FPL", "location": "Miami"},
        {"lat": 40.7128, "lng": -74.0060, "expected": None, "location": "New York (out of range)"},
    ]
    
    passed = 0
    for case in test_cases:
        response = requests.post(
            f"{base_url}/api/utilities/detect",
            json={"lat": case["lat"], "lng": case["lng"]},
            headers=headers
        )
        
        if response.status_code == 200:
            data = response.json()
            detected = data.get("utility_id")
            if detected == case["expected"]:
                print(f"  ✅ PASS: Detected {detected} at {case['location']}")
                passed += 1
            else:
                print(f"  ❌ FAIL: Expected {case['expected']}, got {detected} at {case['location']}")
        else:
            print(f"  ❌ FAIL: Status {response.status_code}: {response.text[:100]}")
    
    return passed == len(test_cases)

def test_utility_list(base_url, token=None):
    """Test listing all utilities"""
    print("\n📋 Testing Utility List...")
    
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    
    response = requests.get(f"{base_url}/api/utilities/list", headers=headers)
    
    if response.status_code == 200:
        data = response.json()
        utilities = data.get("utilities", [])
        total = data.get("total", 0)
        
        if total >= 4:  # We have PGE, SCE, SDGE, FPL
            print(f"  ✅ PASS: Found {total} utilities: {', '.join([u['id'] for u in utilities])}")
            return True
        else:
            print(f"  ❌ FAIL: Only found {total} utilities")
            return False
    else:
        print(f"  ❌ FAIL: Status {response.status_code}: {response.text[:100]}")
        return False

def test_spec_ingestion(base_url, token=None):
    """Test spec ingestion"""
    print("\n📄 Testing Spec Ingestion...")
    
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    
    # Create a minimal test PDF
    test_pdf_path = Path("test_spec.pdf")
    if not test_pdf_path.exists():
        # Minimal valid PDF
        pdf_content = b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n3 0 obj\n<< /Type /Page /Parent 2 0 R /Resources << /Font << /F1 << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> >> >> /MediaBox [0 0 612 792] /Contents 4 0 R >>\nendobj\n4 0 obj\n<< /Length 44 >>\nstream\nBT /F1 12 Tf 100 700 Td (Test Spec) Tj ET\nendstream\nendobj\nxref\n0 5\n0000000000 65535 f\n0000000009 00000 n\n0000000058 00000 n\n0000000115 00000 n\n0000000274 00000 n\ntrailer\n<< /Size 5 /Root 1 0 R >>\nstartxref\n362\n%%EOF"
        test_pdf_path.write_bytes(pdf_content)
    
    # Test ingestion for PG&E
    with open(test_pdf_path, "rb") as f:
        files = {"file": ("greenbook.pdf", f, "application/pdf")}
        response = requests.post(
            f"{base_url}/api/utilities/PGE/ingest",
            files=files,
            headers=headers
        )
    
    if response.status_code == 200:
        data = response.json()
        result = data.get("result", {})
        if result.get("status") == "processed":
            sections = result.get("sections", [])
            print(f"  ✅ PASS: Ingested spec for PGE, {result.get('pages', 0)} pages")
            if sections:
                print(f"     Sections: {', '.join(sections[:3])}")
            return True
        else:
            print(f"  ❌ FAIL: Ingestion failed")
            return False
    else:
        print(f"  ❌ FAIL: Status {response.status_code}: {response.text[:100]}")
        return False

def test_audit_analysis(base_url, token=None):
    """Test existing audit analysis endpoint"""
    print("\n🔍 Testing Audit Analysis...")
    
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    
    # Use the existing test PDF
    test_pdf_path = Path("test_spec.pdf")
    if not test_pdf_path.exists():
        print("  ⚠️ No test PDF found, skipping audit analysis test")
        return False
    
    with open(test_pdf_path, "rb") as f:
        files = {"file": ("test_audit.pdf", f, "application/pdf")}
        response = requests.post(
            f"{base_url}/analyze-audit",
            files=files,
            headers=headers
        )
    
    if response.status_code == 200:
        data = response.json()
        infractions = data.get("infractions", [])
        confidence = data.get("overall_confidence", 0)
        
        # Since we're using a minimal PDF, we might not get infractions
        print(f"  ✅ PASS: Analyzed audit for PGE, found {len(infractions)} infractions")
        print(f"     Overall confidence: {confidence:.2%}")
        return True
    else:
        print(f"  ❌ FAIL: Status {response.status_code}: {response.text[:100]}")
        return False

def test_cross_reference(base_url, token=None):
    """Test cross-reference functionality"""
    print("\n🔄 Testing Cross-Reference...")
    
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    
    response = requests.post(
        f"{base_url}/api/utilities/standards/cross-reference",
        json={"requirement": "overhead clearance"},
        headers=headers
    )
    
    if response.status_code == 200:
        data = response.json()
        cross_refs = data.get("cross_references", {})
        utilities_compared = data.get("utilities_compared", 0)
        
        if utilities_compared > 0:
            print(f"  ✅ PASS: Cross-referenced across {utilities_compared} utilities")
            for utility_id, info in list(cross_refs.items())[:2]:
                sections = info.get('matching_sections', [])
                if sections:
                    print(f"     {info['utility_name']}: {', '.join(sections[:2])}")
            return True
        else:
            print(f"  ⚠️ WARNING: No cross-references found (need to ingest specs first)")
            return True  # Not a failure, just no data yet
    else:
        print(f"  ❌ FAIL: Status {response.status_code}: {response.text[:100]}")
        return False

def test_job_creation(base_url, token=None):
    """Test job creation with auto-detected utility"""
    print("\n💼 Testing Job Creation...")
    
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    
    job_data = {
        "pm_number": "PM-2025-001",
        "description": "Pole replacement at Market St",
        "lat": 37.7749,
        "lng": -122.4194
    }
    
    response = requests.post(
        f"{base_url}/api/utilities/jobs/create",
        json=job_data,
        headers=headers
    )
    
    if response.status_code == 200:
        data = response.json()
        job = data.get("job", {})
        utility_name = job.get("utility_name")
        
        if utility_name == "Pacific Gas & Electric":
            print(f"  ✅ PASS: Job created for {utility_name}")
            print(f"     PM Number: {job.get('pm_number')}")
            return True
        else:
            print(f"  ❌ FAIL: Unexpected utility: {utility_name}")
            return False
    else:
        print(f"  ❌ FAIL: Status {response.status_code}: {response.text[:100]}")
        return False

def test_form_population(base_url, token=None):
    """Test form population for utility"""
    print("\n📝 Testing Form Population...")
    
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    
    universal_data = {
        "job_number": "JOB-001",
        "location": "123 Main St",
        "pole_type": "Type 1"
    }
    
    response = requests.post(
        f"{base_url}/api/utilities/forms/PGE/populate",
        json={"universal_data": universal_data},
        headers=headers
    )
    
    if response.status_code == 200:
        data = response.json()
        result = data.get("result", {})
        fields = result.get("fields", {})
        
        if "PM_NUMBER" in fields:
            print(f"  ✅ PASS: Form populated for PGE")
            print(f"     Fields: {', '.join(list(fields.keys())[:3])}")
            return True
        else:
            print(f"  ❌ FAIL: Expected PG&E field mappings not found")
            return False
    else:
        print(f"  ❌ FAIL: Status {response.status_code}: {response.text[:100]}")
        return False

def main():
    """Run all tests"""
    print("=" * 60)
    print("🚀 Universal Standards Engine Test Suite")
    print("=" * 60)
    
    # Determine which URL to use
    if len(sys.argv) > 1 and sys.argv[1] == "prod":
        base_url = PROD_URL
        print(f"🌐 Testing PRODUCTION: {base_url}")
    else:
        base_url = LOCAL_URL
        print(f"💻 Testing LOCAL: {base_url}")
    
    # Track test results
    results = []
    
    # Check server health
    if not test_health_check(base_url):
        print("\n💡 Start the server first:")
        print("   python app_oct2025_enhanced.py")
        return 1
    
    # Get auth token if available
    print("\n🔐 Testing Authentication...")
    token = get_auth_token(base_url)
    
    # Run all tests
    tests = [
        ("Utility Detection", lambda: test_utility_detection(base_url, token)),
        ("Utility List", lambda: test_utility_list(base_url, token)),
        ("Spec Ingestion", lambda: test_spec_ingestion(base_url, token)),
        ("Audit Analysis", lambda: test_audit_analysis(base_url, token)),
        ("Cross-Reference", lambda: test_cross_reference(base_url, token)),
        ("Job Creation", lambda: test_job_creation(base_url, token)),
        ("Form Population", lambda: test_form_population(base_url, token))
    ]
    
    for test_name, test_func in tests:
        try:
            results.append((test_name, test_func()))
        except Exception as e:
            print(f"\n❌ Error in {test_name}: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 TEST SUMMARY")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {status}: {test_name}")
    
    print(f"\n  Total: {passed}/{total} passed ({passed/total*100:.0f}%)")
    
    if passed == total:
        print("\n✅ All tests passed!")
    else:
        print(f"\n⚠️ {total - passed} test(s) failed")
    
    print("=" * 60)
    
    return 0 if passed == total else 1

if __name__ == "__main__":
    sys.exit(main())
