#!/usr/bin/env python3
"""
Test script for NEXA Production API
Tests all critical endpoints before and after deployment
"""

import requests
import json
import time
import sys
from pathlib import Path

# Configuration
LOCAL_URL = "http://localhost:8000"
PRODUCTION_URL = "https://nexa-doc-analyzer-prod.onrender.com"  # Update after deployment

# Test credentials
TEST_USERNAME = "admin"
TEST_PASSWORD = "Test@Pass123!"

# Color codes for output
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'

def print_test(name, passed, details=""):
    """Print test result with color"""
    status = f"{GREEN}✓ PASS{RESET}" if passed else f"{RED}✗ FAIL{RESET}"
    print(f"  {status} - {name}")
    if details:
        print(f"      {BLUE}→{RESET} {details}")

def test_health(base_url):
    """Test health endpoint"""
    try:
        resp = requests.get(f"{base_url}/health", timeout=5)
        data = resp.json()
        passed = resp.status_code == 200 and data.get('status') == 'healthy'
        print_test(
            "Health Check",
            passed,
            f"Model: {data.get('model_loaded', False)}, Specs: {data.get('specs_loaded', 0)}"
        )
        return passed
    except Exception as e:
        print_test("Health Check", False, str(e))
        return False

def test_root(base_url):
    """Test root endpoint"""
    try:
        resp = requests.get(f"{base_url}/", timeout=5)
        data = resp.json()
        passed = resp.status_code == 200 and data.get('status') == 'operational'
        print_test(
            "Root Endpoint",
            passed,
            f"Version: {data.get('version', 'unknown')}"
        )
        return passed
    except Exception as e:
        print_test("Root Endpoint", False, str(e))
        return False

def test_authentication(base_url):
    """Test authentication"""
    try:
        # Get token
        resp = requests.post(
            f"{base_url}/auth/token",
            params={"username": TEST_USERNAME, "password": TEST_PASSWORD},
            timeout=5
        )
        
        if resp.status_code == 200:
            token = resp.json().get('access_token')
            print_test("Authentication", True, "Token obtained successfully")
            return True, token
        else:
            print_test("Authentication", False, f"Status: {resp.status_code}")
            return False, None
    except Exception as e:
        print_test("Authentication", False, str(e))
        return False, None

def test_spec_upload(base_url, token):
    """Test spec upload (mock)"""
    try:
        # Create mock PDF content
        mock_pdf = b"%PDF-1.4\nMock PG&E Spec Document\nTransformer Installation Guidelines"
        
        headers = {"Authorization": f"Bearer {token}"}
        files = [('files', ('test_spec.pdf', mock_pdf, 'application/pdf'))]
        
        resp = requests.post(
            f"{base_url}/upload-specs",
            headers=headers,
            files=files,
            timeout=10
        )
        
        if resp.status_code == 200:
            data = resp.json()
            print_test(
                "Spec Upload",
                data.get('success', False),
                f"Processed: {data.get('files_processed', 0)}, Chunks: {data.get('total_chunks', 0)}"
            )
            return data.get('success', False)
        else:
            print_test("Spec Upload", False, f"Status: {resp.status_code}")
            return False
    except Exception as e:
        print_test("Spec Upload", False, str(e))
        return False

def test_audit_analysis(base_url, token):
    """Test audit analysis"""
    try:
        # Create mock audit PDF
        mock_audit = b"%PDF-1.4\nAudit Report\nPM-2025-10-001\nInfraction: Missing ground wire"
        
        headers = {"Authorization": f"Bearer {token}"}
        files = {'file': ('audit.pdf', mock_audit, 'application/pdf')}
        data = {'confidence_threshold': 0.6, 'max_results': 5}
        
        resp = requests.post(
            f"{base_url}/analyze-audit",
            headers=headers,
            files=files,
            data=data,
            timeout=10
        )
        
        if resp.status_code == 200:
            result = resp.json()
            print_test(
                "Audit Analysis",
                result.get('success', False),
                f"PM: {result.get('pm_number')}, Infractions: {result.get('total_infractions', 0)}, "
                f"Repealable: {result.get('repealable_count', 0)}"
            )
            return result.get('success', False)
        else:
            print_test("Audit Analysis", False, f"Status: {resp.status_code}")
            return False
    except Exception as e:
        print_test("Audit Analysis", False, str(e))
        return False

def test_spec_library(base_url, token):
    """Test spec library endpoint"""
    try:
        headers = {"Authorization": f"Bearer {token}"}
        resp = requests.get(f"{base_url}/spec-library", headers=headers, timeout=5)
        
        if resp.status_code == 200:
            data = resp.json()
            print_test(
                "Spec Library",
                True,
                f"Files: {data.get('total_files', 0)}, Chunks: {data.get('total_chunks', 0)}"
            )
            return True
        else:
            print_test("Spec Library", False, f"Status: {resp.status_code}")
            return False
    except Exception as e:
        print_test("Spec Library", False, str(e))
        return False

def test_ml_status(base_url, token):
    """Test ML status endpoint"""
    try:
        headers = {"Authorization": f"Bearer {token}"}
        resp = requests.get(f"{base_url}/ml-status", headers=headers, timeout=5)
        
        if resp.status_code == 200:
            data = resp.json()
            healthy = data.get('healthy', False)
            print_test(
                "ML Status",
                healthy,
                f"Torch: {data.get('torch_config', {}).get('version', 'unknown')}"
            )
            return healthy
        else:
            print_test("ML Status", False, f"Status: {resp.status_code}")
            return False
    except Exception as e:
        print_test("ML Status", False, str(e))
        return False

def run_test_suite(base_url, test_name="API"):
    """Run complete test suite"""
    print(f"\n{YELLOW}{'='*60}{RESET}")
    print(f"{YELLOW}Testing {test_name}: {base_url}{RESET}")
    print(f"{YELLOW}{'='*60}{RESET}\n")
    
    results = []
    
    # Basic connectivity
    results.append(test_health(base_url))
    results.append(test_root(base_url))
    
    # Authentication
    auth_passed, token = test_authentication(base_url)
    results.append(auth_passed)
    
    if token:
        # Authenticated endpoints
        results.append(test_spec_upload(base_url, token))
        results.append(test_audit_analysis(base_url, token))
        results.append(test_spec_library(base_url, token))
        results.append(test_ml_status(base_url, token))
    else:
        print(f"  {YELLOW}⚠ Skipping authenticated tests (no token){RESET}")
        results.extend([False] * 4)
    
    # Summary
    passed = sum(results)
    total = len(results)
    success_rate = (passed / total * 100) if total > 0 else 0
    
    print(f"\n{BLUE}Summary: {passed}/{total} tests passed ({success_rate:.0f}%){RESET}")
    
    if passed == total:
        print(f"{GREEN}✓ All tests passed!{RESET}")
    else:
        print(f"{RED}✗ Some tests failed - review logs above{RESET}")
    
    return passed == total

def main():
    """Main test runner"""
    print(f"\n{BLUE}{'='*60}{RESET}")
    print(f"{BLUE}NEXA Production API Test Suite{RESET}")
    print(f"{BLUE}{'='*60}{RESET}")
    
    # Test local if available
    try:
        requests.get(LOCAL_URL, timeout=2)
        local_success = run_test_suite(LOCAL_URL, "Local API")
    except:
        print(f"\n{YELLOW}Local API not available - skipping{RESET}")
        local_success = None
    
    # Ask to test production
    if PRODUCTION_URL != "https://nexa-doc-analyzer-prod.onrender.com":
        print(f"\n{YELLOW}Production URL configured: {PRODUCTION_URL}{RESET}")
        test_prod = input("Test production API? (y/n): ").lower() == 'y'
        
        if test_prod:
            prod_success = run_test_suite(PRODUCTION_URL, "Production API")
        else:
            prod_success = None
    else:
        print(f"\n{YELLOW}Update PRODUCTION_URL after deployment{RESET}")
        prod_success = None
    
    # Final summary
    print(f"\n{BLUE}{'='*60}{RESET}")
    print(f"{BLUE}Final Results:{RESET}")
    if local_success is not None:
        status = f"{GREEN}PASS{RESET}" if local_success else f"{RED}FAIL{RESET}"
        print(f"  Local: {status}")
    if prod_success is not None:
        status = f"{GREEN}PASS{RESET}" if prod_success else f"{RED}FAIL{RESET}"
        print(f"  Production: {status}")
    print(f"{BLUE}{'='*60}{RESET}\n")
    
    # Exit code
    if local_success == False or prod_success == False:
        sys.exit(1)
    else:
        sys.exit(0)

if __name__ == "__main__":
    main()
