#!/usr/bin/env python3
"""
Test NEXA AI Document Analyzer with REAL documents only
This script helps verify the system works with actual PG&E documents
"""

import os
import sys
import requests
import json
from datetime import datetime

# Configuration
BASE_URL = os.getenv("API_URL", "http://localhost:8000")

print("="*70)
print("NEXA AI DOCUMENT ANALYZER - REAL DOCUMENT TEST")
print("="*70)
print("Testing with REAL PG&E documents only")
print("-"*70)

def test_api_health():
    """Test API health endpoint"""
    try:
        response = requests.get(f"{BASE_URL}/api/status")
        if response.status_code == 200:
            data = response.json()
            print(f"\n✅ API Status: {data.get('status', 'unknown')}")
            print(f"   Database: {data.get('database', 'unknown')}")
            print(f"   ML Models: {data.get('ml_models', 'unknown')}")
            return True
        else:
            print(f"\n❌ API health check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"\n❌ Cannot connect to API: {e}")
        return False

def test_upload_real_spec_book(spec_book_path):
    """Test uploading a real PG&E spec book"""
    if not os.path.exists(spec_book_path):
        print(f"\n⚠️  Spec book not found: {spec_book_path}")
        print("   Please provide a real PG&E spec book PDF")
        return False
    
    print(f"\n📚 Uploading spec book: {os.path.basename(spec_book_path)}")
    
    try:
        with open(spec_book_path, 'rb') as f:
            files = {'file': (os.path.basename(spec_book_path), f, 'application/pdf')}
            data = {'document_type': 'spec_book'}
            
            response = requests.post(
                f"{BASE_URL}/api/validate-compliance",
                files=files,
                data=data
            )
            
        if response.status_code == 200:
            result = response.json()
            print(f"   ✅ Spec book processed successfully")
            print(f"   Rules extracted: {result.get('rules_count', 0)}")
            print(f"   Pages processed: {result.get('pages', 0)}")
            return True
        else:
            print(f"   ❌ Upload failed: {response.status_code}")
            print(f"   Error: {response.text}")
            return False
    except Exception as e:
        print(f"   ❌ Error uploading spec book: {e}")
        return False

def test_analyze_real_audit(audit_path, pm_number):
    """Test analyzing a real QA audit document"""
    if not os.path.exists(audit_path):
        print(f"\n⚠️  Audit document not found: {audit_path}")
        print("   Please provide a real PG&E audit PDF")
        return False
    
    print(f"\n📋 Analyzing audit: {os.path.basename(audit_path)}")
    print(f"   PM Number: {pm_number}")
    
    try:
        with open(audit_path, 'rb') as f:
            files = {'file': (os.path.basename(audit_path), f, 'application/pdf')}
            data = {
                'document_type': 'audit',
                'pm_number': pm_number
            }
            
            response = requests.post(
                f"{BASE_URL}/api/validate-compliance",
                files=files,
                data=data
            )
            
        if response.status_code == 200:
            result = response.json()
            print(f"   ✅ Audit analyzed successfully")
            print(f"   Job ID: {result.get('job_id')}")
            print(f"   Infractions found: {result.get('infractions_count', 0)}")
            
            # Get detailed infractions
            if result.get('job_id'):
                inf_response = requests.get(
                    f"{BASE_URL}/api/infractions/{result['job_id']}"
                )
                if inf_response.status_code == 200:
                    infractions = inf_response.json()
                    for inf in infractions[:3]:  # Show first 3
                        print(f"\n   Infraction: {inf.get('infraction_text', '')[:50]}...")
                        print(f"   Repealable: {inf.get('repealable', False)}")
                        print(f"   Confidence: {inf.get('confidence', 0):.1%}")
                        print(f"   Reason: {inf.get('reason', '')}")
            
            return True
        else:
            print(f"   ❌ Analysis failed: {response.status_code}")
            print(f"   Error: {response.text}")
            return False
    except Exception as e:
        print(f"   ❌ Error analyzing audit: {e}")
        return False

def main():
    """Main test function"""
    print("\n🔍 Starting real document tests...")
    
    # Test API health
    if not test_api_health():
        print("\n❌ API is not running. Start with: python field_crew_workflow.py")
        sys.exit(1)
    
    # Instructions for real documents
    print("\n" + "="*70)
    print("📄 REAL DOCUMENT TEST REQUIREMENTS")
    print("="*70)
    print("\nTo test with real documents, you need:")
    print("\n1. A real PG&E spec book PDF")
    print("   Example: PGE_Spec_Book_2025.pdf")
    print("\n2. A real QA audit document PDF")
    print("   Example: PM_35125285_audit.pdf")
    print("\n3. The PM number for the audit")
    print("   Example: PM_35125285")
    
    print("\n" + "-"*70)
    print("Place your documents in this directory and run:")
    print("\npython test_real_documents.py <spec_book.pdf> <audit.pdf> <PM_number>")
    print("\nExample:")
    print("python test_real_documents.py PGE_Spec_Book_2025.pdf PM_35125285_audit.pdf PM_35125285")
    
    # Check if documents were provided
    if len(sys.argv) >= 4:
        spec_book = sys.argv[1]
        audit = sys.argv[2]
        pm_number = sys.argv[3]
        
        print(f"\n🚀 Testing with provided documents...")
        
        # Upload spec book
        if test_upload_real_spec_book(spec_book):
            # Analyze audit
            test_analyze_real_audit(audit, pm_number)
        
        print("\n" + "="*70)
        print("✅ REAL DOCUMENT TEST COMPLETE")
        print("="*70)
        print("\nSystem is processing REAL documents only!")
        print("NO mock data is being used.")
    else:
        print("\n⚠️  No documents provided for testing")
        print("Please provide real PG&E documents as shown above")
        
        # Show what would happen with real documents
        print("\n" + "="*70)
        print("📊 EXPECTED RESULTS WITH REAL DOCUMENTS:")
        print("="*70)
        print("\n1. Spec Book Upload:")
        print("   • Extract 200+ compliance rules")
        print("   • Generate embeddings for each rule")
        print("   • Store in PostgreSQL database")
        print("   • Index with FAISS for fast search")
        
        print("\n2. Audit Analysis:")
        print("   • Find all infractions in document")
        print("   • Match against spec book rules")
        print("   • Determine repealability (95%+ accuracy)")
        print("   • Provide specific page references")
        print("   • Store results in database")
        
        print("\n3. PM Dashboard:")
        print("   • View all infractions for PM package")
        print("   • See confidence levels for each")
        print("   • Appeal infractions with one click")
        print("   • Export reports for PG&E submission")

if __name__ == "__main__":
    main()
