#!/usr/bin/env python3
"""
Test Universal Standards Platform
Quick tests to verify all features work
"""
import requests
import json
import sys

# Configuration
BASE_URL = "https://nexa-us-pro.onrender.com"
# For local testing: BASE_URL = "http://localhost:8000"

def test_health():
    """Test health endpoint"""
    print("🏥 Testing health check...")
    resp = requests.get(f"{BASE_URL}/health")
    if resp.status_code == 200:
        data = resp.json()
        print(f"✅ Health: {data['status']}")
        print(f"   Utilities: {data.get('utilities_loaded', 0)}")
        print(f"   Standards: {data.get('standards_count', 0)}")
        return True
    else:
        print(f"❌ Health check failed: {resp.status_code}")
        return False

def test_utilities():
    """Test utilities listing"""
    print("\n🏢 Testing utilities list...")
    resp = requests.get(f"{BASE_URL}/api/utilities")
    if resp.status_code == 200:
        data = resp.json()
        utilities = data.get('utilities', [])
        print(f"✅ Found {len(utilities)} utilities:")
        for u in utilities:
            print(f"   - {u}")
        return True
    else:
        print(f"❌ Utilities list failed: {resp.status_code}")
        return False

def test_utility_detection():
    """Test utility detection by location"""
    print("\n📍 Testing utility detection...")
    
    test_locations = [
        {"lat": 37.7749, "lng": -122.4194, "address": "San Francisco, CA", "expected": "PGE"},
        {"lat": 34.0522, "lng": -118.2437, "address": "Los Angeles, CA", "expected": "SCE"},
        {"lat": 25.7617, "lng": -80.1918, "address": "Miami, FL", "expected": "FPL"},
        {"lat": 40.7128, "lng": -74.0060, "address": "New York, NY", "expected": "CONED"}
    ]
    
    for loc in test_locations:
        resp = requests.post(
            f"{BASE_URL}/api/utilities/detect",
            data={
                "lat": loc["lat"],
                "lng": loc["lng"],
                "address": loc["address"]
            }
        )
        
        if resp.status_code == 200:
            data = resp.json()
            detected = data.get('detected_utility')
            if detected == loc['expected']:
                print(f"✅ {loc['address']}: {detected} (correct)")
            else:
                print(f"⚠️ {loc['address']}: {detected} (expected {loc['expected']})")
        else:
            print(f"❌ Detection failed for {loc['address']}: {resp.status_code}")
    
    return True

def test_job_creation():
    """Test job creation with auto-detection"""
    print("\n💼 Testing job creation...")
    
    resp = requests.post(
        f"{BASE_URL}/api/jobs/create",
        data={
            "organization_id": "demo",
            "job_number": "TEST-JOB-001",
            "lat": 37.7749,
            "lng": -122.4194,
            "address": "123 Market St, San Francisco, CA",
            "job_type": "installation"
        }
    )
    
    if resp.status_code == 200:
        data = resp.json()
        print(f"✅ Job created: {data['job_id']}")
        print(f"   Utility: {data['detected_utility']}")
        print(f"   Location: {data['location']['address']}")
        return data['job_id']
    else:
        print(f"❌ Job creation failed: {resp.status_code}")
        print(f"   Response: {resp.text}")
        return None

def test_form_population(job_id):
    """Test form population"""
    print("\n📝 Testing form population...")
    
    if not job_id:
        print("⚠️ Skipping - no job ID")
        return False
    
    form_data = {
        "job_number": "TEST-JOB-001",
        "inspection_date": "2025-10-12",
        "inspector_name": "John Doe",
        "pole_number": "P-12345",
        "pole_height": 45,
        "clearance_horizontal": 12,
        "clearance_vertical": 8,
        "grounding_present": True,
        "notes": "Test inspection"
    }
    
    resp = requests.post(
        f"{BASE_URL}/api/forms/populate",
        data={
            "job_id": job_id,
            "form_type": "inspection",
            "form_data": json.dumps(form_data)
        }
    )
    
    if resp.status_code == 200:
        data = resp.json()
        print(f"✅ Form populated for utility: {data['utility']}")
        print(f"   Validation: {data['validation']['is_valid']}")
        if not data['validation']['is_valid']:
            print(f"   Errors: {data['validation']['errors']}")
        return True
    else:
        print(f"❌ Form population failed: {resp.status_code}")
        return False

def test_cross_reference():
    """Test cross-reference standards"""
    print("\n🔍 Testing cross-reference...")
    
    resp = requests.post(
        f"{BASE_URL}/api/standards/cross-reference",
        data={
            "query": "minimum clearance for 12kV lines"
        }
    )
    
    if resp.status_code == 200:
        data = resp.json()
        print(f"✅ Cross-reference found {data['utilities_found']} utilities")
        for utility, standards in data.get('standards_by_utility', {}).items():
            print(f"   {utility}: {len(standards)} standards")
        return True
    else:
        print(f"❌ Cross-reference failed: {resp.status_code}")
        return False

def test_stats():
    """Test statistics endpoint"""
    print("\n📊 Testing statistics...")
    
    resp = requests.get(f"{BASE_URL}/api/stats")
    if resp.status_code == 200:
        data = resp.json()
        print(f"✅ Platform stats:")
        print(f"   Utilities: {data.get('utilities', 0)}")
        print(f"   Standards: {data.get('total_standards', 0)}")
        print(f"   Jobs: {data.get('total_jobs', 0)}")
        print(f"   Forms: {data.get('total_forms', 0)}")
        
        if 'by_utility' in data:
            print(f"   Standards by utility:")
            for utility, count in data['by_utility'].items():
                print(f"     - {utility}: {count}")
        
        return True
    else:
        print(f"❌ Stats failed: {resp.status_code}")
        return False

def main():
    """Run all tests"""
    print("=" * 50)
    print("🧪 NEXA UNIVERSAL STANDARDS PLATFORM TEST SUITE")
    print("=" * 50)
    print(f"Testing: {BASE_URL}")
    print("")
    
    tests_passed = 0
    tests_total = 7
    
    # Run tests
    if test_health():
        tests_passed += 1
    
    if test_utilities():
        tests_passed += 1
    
    if test_utility_detection():
        tests_passed += 1
    
    job_id = test_job_creation()
    if job_id:
        tests_passed += 1
    
    if test_form_population(job_id):
        tests_passed += 1
    
    if test_cross_reference():
        tests_passed += 1
    
    if test_stats():
        tests_passed += 1
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 TEST SUMMARY")
    print("=" * 50)
    print(f"Passed: {tests_passed}/{tests_total}")
    
    if tests_passed == tests_total:
        print("🎉 ALL TESTS PASSED! Platform is fully operational!")
    elif tests_passed > tests_total / 2:
        print("⚠️ Some tests failed. Check logs for details.")
    else:
        print("❌ Major issues detected. Review deployment.")
    
    return tests_passed == tests_total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
