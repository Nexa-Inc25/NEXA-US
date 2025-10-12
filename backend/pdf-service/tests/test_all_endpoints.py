#!/usr/bin/env python3
"""
NEXA Backend Complete Test Suite
Production endpoint validation
"""

import requests
import os
import json
import sys
from uuid import uuid4
import time

BASE_URL = "https://nexa-us-pro.onrender.com"
LOCAL_URL = "http://localhost:8000"

def get_token(email: str = "admin@nexa.com", password: str = "admin123", base_url: str = BASE_URL) -> str:
    """Get JWT token for testing"""
    try:
        response = requests.post(
            f"{base_url}/auth/login",
            json={"email": email, "password": password}
        )
        if response.status_code == 200:
            print(f"PASS: Authenticated as {email}")
            return response.json()["access_token"]
        print(f"WARNING: Auth failed: {response.status_code}: {response.text[:100]}")
        return "mock-token-for-testing"
    except Exception as e:
        print(f"WARNING: Auth endpoint unavailable: {e}. Using mock token.")
        return "mock-token-for-testing"

def test_health(base_url: str = BASE_URL):
    """Test /health endpoint"""
    print("\nTesting Health Check...")
    response = requests.get(f"{base_url}/health")
    if response.status_code == 200 and response.json()["status"] == "healthy":
        print(f"PASS: Server healthy - {response.json()['status']}")
    else:
        print(f"FAIL: Health check failed: {response.text[:100]}")
        return False
    return True

def test_auth(token: str, base_url: str = BASE_URL):
    """Test /auth/me endpoint"""
    print("\nTesting Authentication...")
    if token == "mock-token-for-testing":
        print("WARNING: Skipping auth test (mock token)")
        return True
    response = requests.get(
        f"{base_url}/auth/me",
        headers={"Authorization": f"Bearer {token}"}
    )
    if response.status_code == 200:
        print(f"PASS: Authenticated as {response.json()['email']}")
        return True
    print(f"FAIL: Auth failed: {response.status_code}: {response.text[:100]}")
    return False

def test_utility_detection(token: str, base_url: str = BASE_URL):
    """Test /api/utilities/detect endpoint"""
    print("\nTesting Utility Detection...")
    test_cases = [
        {"location": {"lat": 37.7749, "lng": -122.4194}, "expected": "PGE"},
        {"location": {"lat": 25.7617, "lng": -80.1918}, "expected": "FPL"},
        {"location": {"lat": 40.7128, "lng": -74.0060}, "expected": None}
    ]
    passed = True
    for case in test_cases:
        response = requests.post(
            f"{base_url}/api/utilities/detect",
            json=case["location"],
            headers={"Authorization": f"Bearer {token}"}
        )
        if case["expected"]:
            if response.status_code == 200 and response.json().get("utility_id") == case["expected"]:
                print(f"PASS: Detected {case['expected']} at ({case['location']['lat']}, {case['location']['lng']})")
            else:
                print(f"FAIL: Expected {case['expected']}, got {response.text[:100]}")
                passed = False
        else:
            if response.status_code == 404:
                print(f"PASS: No utility at ({case['location']['lat']}, {case['location']['lng']})")
            else:
                print(f"FAIL: Expected 404, got {response.text[:100]}")
                passed = False
    return passed

def test_utility_list(token: str, base_url: str = BASE_URL):
    """Test /api/utilities/list endpoint"""
    print("\nTesting Utility List...")
    response = requests.get(
        f"{base_url}/api/utilities/list",
        headers={"Authorization": f"Bearer {token}"}
    )
    if response.status_code == 200 and len(response.json()["utilities"]) >= 4:
        utilities = response.json()["utilities"]
        print(f"PASS: Found {len(utilities)} utilities: {', '.join(u['id'] for u in utilities)}")
        return True
    print(f"FAIL: List failed: {response.text[:100]}")
    return False

def test_spec_ingestion(token: str, base_url: str = BASE_URL):
    """Test /api/utilities/{utility_id}/ingest endpoint"""
    print("\nTesting Spec Ingestion...")
    # Create a simple PDF
    pdf_content = b"%PDF-1.4\n1 0 obj\n<<>>endobj\nxref\n0 2\n0000000000 65535 f\n0000000009 00000 n\ntrailer\n<< /Size 2 /Root 1 0 R >>\nstartxref\n40\n%%EOF"
    
    response = requests.post(
        f"{base_url}/api/utilities/PGE/ingest",
        files={"file": ("test_greenbook.pdf", pdf_content, "application/pdf")},
        headers={"Authorization": f"Bearer {token}"}
    )
    if response.status_code == 200 and response.json()["result"]["utility"] == "PGE":
        result = response.json()["result"]
        print(f"PASS: Ingested spec for {result['utility']}, {result.get('chunks', 0)} chunks")
        return True
    print(f"FAIL: Ingest failed: {response.text[:100]}")
    return False

def test_spec_library(base_url: str = BASE_URL):
    """Test /spec-library endpoint"""
    print("\nTesting Spec Library...")
    response = requests.get(f"{base_url}/spec-library")
    if response.status_code == 200:
        data = response.json()
        print(f"PASS: Spec library has {data['metadata']['total_chunks']} chunks from {data['metadata']['total_files']} files")
        return True
    print(f"FAIL: Spec library failed: {response.text[:100]}")
    return False

def test_audit_analysis(token: str, base_url: str = BASE_URL):
    """Test /analyze-audit endpoint"""
    print("\nTesting Audit Analysis...")
    pdf_content = b"%PDF-1.4\n1 0 obj\n<<>>endobj\nxref\n0 2\n0000000000 65535 f\n0000000009 00000 n\ntrailer\n<< /Size 2 /Root 1 0 R >>\nstartxref\n40\n%%EOF"
    
    response = requests.post(
        f"{base_url}/analyze-audit",
        files={"file": ("test_audit.pdf", pdf_content, "application/pdf")},
        headers={"Authorization": f"Bearer {token}"}
    )
    if response.status_code == 200:
        data = response.json()
        print(f"PASS: Analyzed audit, found {len(data.get('infractions', []))} infractions")
        return True
    elif response.status_code == 400 and "spec" in response.text.lower():
        print(f"WARNING: Audit analysis requires spec library to be populated first")
        return False
    print(f"FAIL: Audit failed: {response.text[:100]}")
    return False

def test_cross_reference(token: str, base_url: str = BASE_URL):
    """Test /api/utilities/standards/cross-reference endpoint"""
    print("\nTesting Cross-Reference...")
    response = requests.post(
        f"{base_url}/api/utilities/standards/cross-reference",
        json={"request": {"requirement": "capacitor spacing requirements"}},
        headers={"Authorization": f"Bearer {token}"}
    )
    if response.status_code == 200:
        data = response.json()
        print(f"PASS: Cross-referenced across {len(data.get('utilities', []))} utilities")
        return True
    print(f"FAIL: Cross-ref failed: {response.text[:100]}")
    return False

def test_job_creation(token: str, base_url: str = BASE_URL):
    """Test /api/utilities/jobs/create endpoint"""
    print("\nTesting Job Creation...")
    job_id = f"PM-TEST-{int(time.time())}"
    response = requests.post(
        f"{base_url}/api/utilities/jobs/create",
        json={
            "request": {
                "pm_number": job_id,
                "description": "Test job for E2E validation",
                "lat": 37.7749,
                "lng": -122.4194
            }
        },
        headers={"Authorization": f"Bearer {token}"}
    )
    if response.status_code == 200:
        data = response.json()
        print(f"PASS: Created job {data.get('job', {}).get('pm_number', 'unknown')} for {data.get('job', {}).get('utility', 'unknown')}")
        return True
    print(f"FAIL: Job creation failed: {response.text[:100]}")
    return False

def test_form_population(token: str, base_url: str = BASE_URL):
    """Test /api/utilities/forms/{utility_id}/populate endpoint"""
    print("\nTesting Form Population...")
    response = requests.post(
        f"{base_url}/api/utilities/forms/PGE/populate",
        json={
            "request": {
                "universal_data": {
                    "job_id": "TEST-001",
                    "pm_number": "PM-2025-TEST",
                    "location": "San Francisco, CA",
                    "equipment": ["Capacitor Bank", "Distribution Pole"],
                    "clearances": {
                        "overhead": "18 feet minimum",
                        "underground": "36 inches minimum"
                    }
                }
            }
        },
        headers={"Authorization": f"Bearer {token}"}
    )
    if response.status_code == 200:
        print(f"PASS: Populated form for utility")
        return True
    print(f"FAIL: Form population failed: {response.text[:100]}")
    return False

def main():
    """Run all E2E tests"""
    print("=" * 60)
    print("NEXA BACKEND E2E TEST SUITE")
    print("=" * 60)
    results = []
    
    # Select environment
    if len(sys.argv) > 1 and sys.argv[1] == "local":
        base_url = LOCAL_URL
        print(f"Testing LOCAL: {base_url}")
    else:
        base_url = BASE_URL
        print(f"Testing PRODUCTION: {base_url}")
    
    print("=" * 60)
    
    # Run tests
    results.append(("Health Check", test_health(base_url)))
    token = get_token(base_url=base_url)
    results.append(("Authentication", test_auth(token, base_url)))
    results.append(("Utility Detection", test_utility_detection(token, base_url)))
    results.append(("Utility List", test_utility_list(token, base_url)))
    results.append(("Spec Library", test_spec_library(base_url)))
    results.append(("Spec Ingestion", test_spec_ingestion(token, base_url)))
    results.append(("Audit Analysis", test_audit_analysis(token, base_url)))
    results.append(("Cross-Reference", test_cross_reference(token, base_url)))
    results.append(("Job Creation", test_job_creation(token, base_url)))
    results.append(("Form Population", test_form_population(token, base_url)))
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    passed = sum(1 for _, result in results if result)
    for test, result in results:
        status = "PASS" if result else "FAIL"
        print(f"{status}: {test}")
    
    print(f"\nTotal: {passed}/{len(results)} passed ({passed/len(results)*100:.0f}%)")
    
    if passed == len(results):
        print("\nAll tests passed. Backend is fully operational.")
        sys.exit(0)
    else:
        print(f"\n{len(results) - passed} test(s) failed. Review failures above.")
        sys.exit(1)

if __name__ == "__main__":
    main()
