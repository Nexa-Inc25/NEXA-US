#!/usr/bin/env python3
"""
NEXA Document Analyzer Workflow Test Script
Tests the complete spec learning and audit analysis workflow
"""

import requests
import json
import time
from pathlib import Path

# Configuration
ANALYZER_URL = "https://nexa-doc-analyzer-oct2025.onrender.com"
DASHBOARD_URL = "https://nexa-dashboard.onrender.com"

def test_health():
    """Test if the analyzer service is healthy"""
    print("🔍 Testing analyzer health...")
    try:
        response = requests.get(f"{ANALYZER_URL}/health", timeout=10)
        if response.status_code == 200:
            print("✅ Analyzer is healthy!")
            return True
        else:
            print(f"❌ Health check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Cannot reach analyzer: {e}")
        return False

def upload_spec(pdf_path):
    """Upload a specification PDF for learning"""
    print(f"\n📚 Uploading spec: {pdf_path}")
    
    if not Path(pdf_path).exists():
        print(f"❌ File not found: {pdf_path}")
        return False
    
    try:
        with open(pdf_path, 'rb') as f:
            files = {'file': (Path(pdf_path).name, f, 'application/pdf')}
            response = requests.post(
                f"{ANALYZER_URL}/learn-spec/",
                files=files,
                timeout=60
            )
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Spec uploaded successfully!")
            print(f"   - Chunks created: {result.get('chunks_created', 'N/A')}")
            print(f"   - Processing time: {result.get('processing_time', 'N/A')}s")
            return True
        else:
            print(f"❌ Upload failed: {response.status_code}")
            print(f"   Error: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Upload error: {e}")
        return False

def analyze_audit(pdf_path):
    """Analyze an audit document for infractions"""
    print(f"\n🔎 Analyzing audit: {pdf_path}")
    
    if not Path(pdf_path).exists():
        print(f"❌ File not found: {pdf_path}")
        return None
    
    try:
        with open(pdf_path, 'rb') as f:
            files = {'file': (Path(pdf_path).name, f, 'application/pdf')}
            response = requests.post(
                f"{ANALYZER_URL}/analyze-audit/",
                files=files,
                timeout=60
            )
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Analysis complete!")
            
            # Display results
            infractions = result.get('infractions', [])
            print(f"\n📊 Found {len(infractions)} infractions:")
            
            for idx, infr in enumerate(infractions, 1):
                print(f"\n  {idx}. {infr.get('code', 'N/A')}")
                print(f"     - Repealable: {infr.get('is_repealable', 'Unknown')}")
                print(f"     - Confidence: {infr.get('confidence', 0):.1%}")
                print(f"     - Reason: {infr.get('reason', 'N/A')}")
                
                spec_refs = infr.get('spec_references', [])
                if spec_refs:
                    print(f"     - Spec References:")
                    for ref in spec_refs[:2]:  # Show first 2 refs
                        print(f"       • {ref}")
            
            return result
        else:
            print(f"❌ Analysis failed: {response.status_code}")
            print(f"   Error: {response.text}")
            return None
    except Exception as e:
        print(f"❌ Analysis error: {e}")
        return None

def test_workflow():
    """Run the complete workflow test"""
    print("="*60)
    print("🚀 NEXA Document Analyzer Workflow Test")
    print("="*60)
    
    # Step 1: Health Check
    if not test_health():
        print("\n⚠️  Analyzer not responding. Check the service.")
        return
    
    # Step 2: Upload Spec (if you have one)
    spec_file = "test_documents/pge_spec_sample.pdf"
    if Path(spec_file).exists():
        upload_spec(spec_file)
    else:
        print(f"\n⚠️  No spec file found at {spec_file}")
        print("   Create a test spec PDF or use an actual PG&E spec")
    
    # Step 3: Analyze Audit (if you have one)
    audit_file = "test_documents/qa_audit_sample.pdf"
    if Path(audit_file).exists():
        analyze_audit(audit_file)
    else:
        print(f"\n⚠️  No audit file found at {audit_file}")
        print("   Create a test audit PDF with infractions")
    
    # Step 4: Check Dashboard
    print(f"\n🌐 Dashboard Status:")
    print(f"   URL: {DASHBOARD_URL}")
    try:
        response = requests.get(DASHBOARD_URL, timeout=10)
        if response.status_code == 200:
            print("   ✅ Dashboard is accessible")
        else:
            print(f"   ❌ Dashboard returned: {response.status_code}")
    except Exception as e:
        print(f"   ❌ Cannot reach dashboard: {e}")
    
    print("\n" + "="*60)
    print("✅ Workflow test complete!")
    print("\nNext Steps:")
    print("1. Upload real PG&E spec PDFs")
    print("2. Test with actual QA audit documents")
    print("3. Check dashboard for results visualization")
    print("4. Monitor logs in Render dashboard")
    print("="*60)

if __name__ == "__main__":
    test_workflow()
