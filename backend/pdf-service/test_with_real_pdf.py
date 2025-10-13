#!/usr/bin/env python3
"""
Test NEXA Backend with Real PDF Document
"""

import requests
import sys
import os
from pathlib import Path

def test_audit_with_real_pdf(pdf_path: str):
    """Test audit analysis with a real PDF"""
    
    # Verify file exists
    if not os.path.exists(pdf_path):
        print(f"ERROR: File not found: {pdf_path}")
        return False
    
    # Get file size
    file_size = os.path.getsize(pdf_path) / (1024 * 1024)  # MB
    print(f"Testing with: {pdf_path}")
    print(f"File size: {file_size:.2f} MB")
    
    # API endpoint
    base_url = "https://nexa-us-pro.onrender.com"
    
    print("\n" + "="*60)
    print("TESTING NEXA BACKEND WITH REAL PDF")
    print("="*60)
    
    # Test 1: Health Check
    print("\n1. Health Check...")
    response = requests.get(f"{base_url}/health")
    if response.status_code == 200:
        print("   PASS: Service is healthy")
    else:
        print(f"   FAIL: {response.status_code}")
    
    # Test 2: Spec Ingestion (as PGE spec)
    print("\n2. Ingesting document as PGE spec...")
    with open(pdf_path, 'rb') as f:
        response = requests.post(
            f"{base_url}/api/utilities/PGE/ingest",
            files={'file': (os.path.basename(pdf_path), f, 'application/pdf')}
        )
    
    if response.status_code == 200:
        data = response.json()
        print(f"   PASS: Ingested for {data['result']['utility']}")
        print(f"   Chunks created: {data['result'].get('chunks', 0)}")
        print(f"   Pages: {data['result'].get('pages', 'unknown')}")
    else:
        print(f"   FAIL: {response.status_code}")
        print(f"   Error: {response.text[:200]}")
    
    # Test 3: Analyze as Audit
    print("\n3. Analyzing document as audit...")
    with open(pdf_path, 'rb') as f:
        response = requests.post(
            f"{base_url}/analyze-audit",
            files={'file': (os.path.basename(pdf_path), f, 'application/pdf')},
            params={'utility_id': 'PGE'}
        )
    
    if response.status_code == 200:
        data = response.json()
        print(f"   PASS: Audit analyzed")
        print(f"   Job ID: {data.get('job_id', 'N/A')}")
        print(f"   Utility: {data.get('utility', 'N/A')}")
        print(f"   Infractions found: {len(data.get('infractions', []))}")
        
        # Show infractions if any
        if data.get('infractions'):
            print("\n   Infractions detected:")
            for i, inf in enumerate(data['infractions'][:3], 1):  # Show first 3
                print(f"   {i}. {inf.get('description', 'No description')}")
                print(f"      Status: {inf.get('status', 'unknown')}")
                print(f"      Confidence: {inf.get('confidence', 0):.2%}")
    else:
        print(f"   FAIL: {response.status_code}")
        print(f"   Error: {response.text[:200]}")
    
    # Test 4: Check Spec Library
    print("\n4. Checking spec library...")
    response = requests.get(f"{base_url}/spec-library")
    if response.status_code == 200:
        data = response.json()
        print(f"   PASS: Library accessible")
        print(f"   Total files: {data.get('total_files', 0)}")
        print(f"   Total chunks: {data.get('total_chunks', 0)}")
    else:
        print(f"   FAIL: {response.status_code}")
    
    # Test 5: Cross-Reference Standards
    print("\n5. Testing cross-reference with your document...")
    response = requests.post(
        f"{base_url}/api/utilities/standards/cross-reference",
        json={"requirement": "clearance requirements"}
    )
    
    if response.status_code == 200:
        data = response.json()
        print(f"   PASS: Cross-reference working")
        print(f"   Utilities compared: {len(data.get('utilities', []))}")
    else:
        print(f"   FAIL: {response.status_code}")
    
    print("\n" + "="*60)
    print("TEST COMPLETE")
    print("="*60)
    
    return True

def main():
    """Main entry point"""
    if len(sys.argv) < 2:
        print("Usage: python test_with_real_pdf.py <path_to_pdf>")
        print("Example: python test_with_real_pdf.py C:\\Documents\\spec.pdf")
        sys.exit(1)
    
    pdf_path = sys.argv[1]
    
    # Handle drag-and-drop quotes
    if pdf_path.startswith('"') and pdf_path.endswith('"'):
        pdf_path = pdf_path[1:-1]
    
    test_audit_with_real_pdf(pdf_path)

if __name__ == "__main__":
    main()
