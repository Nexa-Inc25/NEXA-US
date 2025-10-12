"""
Test script for NEXA AI Document Analyzer API (October 2025 Version)
"""
import requests
import os
import sys
from pathlib import Path

# Configuration
BASE_URL = "http://localhost:8000"  # Change to Render URL when deployed

def test_health():
    """Test health endpoint"""
    print("Testing /health endpoint...")
    response = requests.get(f"{BASE_URL}/health")
    if response.status_code == 200:
        data = response.json()
        print(f"✓ Health check passed")
        print(f"  - Status: {data.get('status')}")
        print(f"  - Device: {data.get('device')}")
        print(f"  - OCR: {data.get('ocr_status')}")
        print(f"  - Spec learned: {data.get('spec_learned')}")
        return True
    else:
        print(f"✗ Health check failed: {response.status_code}")
        return False

def test_root():
    """Test root endpoint"""
    print("\nTesting / endpoint...")
    response = requests.get(f"{BASE_URL}/")
    if response.status_code == 200:
        data = response.json()
        print(f"✓ Root endpoint accessible")
        print(f"  - Name: {data.get('name')}")
        print(f"  - Version: {data.get('version')}")
        print(f"  - OCR Available: {data.get('ocr_available')}")
        print(f"  - PG&E Patterns: {', '.join(data.get('pge_patterns_supported', []))}")
        return True
    else:
        print(f"✗ Root endpoint failed: {response.status_code}")
        return False

def test_upload_spec(spec_file_path):
    """Test spec book upload"""
    print(f"\nTesting spec book upload with: {spec_file_path}")
    
    if not os.path.exists(spec_file_path):
        print(f"✗ File not found: {spec_file_path}")
        return False
    
    with open(spec_file_path, 'rb') as f:
        files = {'file': (os.path.basename(spec_file_path), f, 'application/pdf')}
        response = requests.post(
            f"{BASE_URL}/upload-spec-book",
            files=files,
            params={'use_ocr': True}
        )
    
    if response.status_code == 200:
        data = response.json()
        print(f"✓ Spec book uploaded successfully")
        print(f"  - Chunks learned: {data.get('chunks_learned')}")
        print(f"  - Documents processed: {data.get('documents_processed')}")
        print(f"  - OCR used: {data.get('ocr_used')}")
        print(f"  - Storage path: {data.get('storage_path')}")
        return True
    else:
        print(f"✗ Upload failed: {response.status_code}")
        print(f"  Response: {response.text}")
        return False

def test_analyze_audit(audit_file_path):
    """Test audit analysis"""
    print(f"\nTesting audit analysis with: {audit_file_path}")
    
    if not os.path.exists(audit_file_path):
        print(f"✗ File not found: {audit_file_path}")
        return False
    
    with open(audit_file_path, 'rb') as f:
        files = {'file': (os.path.basename(audit_file_path), f, 'application/pdf')}
        response = requests.post(
            f"{BASE_URL}/analyze-audit",
            files=files,
            params={'use_ocr': True, 'confidence_threshold': 0.5}
        )
    
    if response.status_code == 200:
        data = response.json()
        print(f"✓ Audit analyzed successfully")
        print(f"  - Infractions found: {len(data)}")
        
        for i, inf in enumerate(data[:3], 1):  # Show first 3
            print(f"\n  Infraction {i}:")
            print(f"    - Status: {inf.get('status')}")
            print(f"    - Confidence: {inf.get('confidence')}%")
            print(f"    - Matches: {inf.get('match_count')}")
            print(f"    - PG&E Docs: {', '.join(inf.get('matched_documents', []))}")
            print(f"    - Text: {inf.get('infraction')[:100]}...")
            
            reasons = inf.get('reasons', [])
            if reasons:
                print(f"    - Reasons:")
                for reason in reasons[:2]:
                    print(f"      • {reason[:100]}...")
        
        return True
    else:
        print(f"✗ Analysis failed: {response.status_code}")
        print(f"  Response: {response.text}")
        return False

def create_sample_audit():
    """Create a sample audit PDF with infractions"""
    print("\n Creating sample audit content...")
    
    # Sample infractions based on PG&E documents
    sample_text = """
    QUALITY ASSURANCE AUDIT REPORT
    Date: October 6, 2025
    Project: Distribution Line Upgrade
    
    FINDINGS:
    
    1. Go-back infraction: Missing guy marker on anchor per document 06542
       Location: Pole #12345
       Severity: Medium
    
    2. Violation: Guy grip installation incorrect according to 06537 Rev. #4
       Location: Span 23-24
       Severity: High
    
    3. Non-compliance: Cable grip not installed per document 022277
       Location: Riser pole #45678
       Severity: Low
    
    4. Issue: Molding height does not meet standard 022282 requirements
       Location: Building entrance
       Severity: Medium
    
    5. Go-back: Incorrect pole line guy tension per document 06543
       Location: Corner pole #78901
       Severity: High
    
    END OF REPORT
    """
    
    print("Sample audit content (for testing):")
    print(sample_text)
    return sample_text

def main():
    """Run all tests"""
    print("=" * 60)
    print("NEXA AI Document Analyzer API Test Suite")
    print("October 2025 Version - PG&E Enhanced")
    print("=" * 60)
    
    # Test endpoints
    if not test_health():
        print("\n⚠️  API not running. Start with: uvicorn app_oct2025:app --port 8000")
        return
    
    test_root()
    
    # Check for test files
    print("\n" + "=" * 60)
    print("File Upload Tests")
    print("=" * 60)
    
    # Look for spec PDFs
    spec_dir = Path(".")
    spec_files = list(spec_dir.glob("*.pdf"))
    
    if spec_files:
        print(f"\nFound {len(spec_files)} PDF files:")
        for f in spec_files[:5]:
            print(f"  - {f.name}")
        
        # Test with first spec file
        if input("\nUpload first PDF as spec book? (y/n): ").lower() == 'y':
            test_upload_spec(spec_files[0])
            
            # Create and test sample audit
            if input("\nCreate and test sample audit? (y/n): ").lower() == 'y':
                audit_content = create_sample_audit()
                # Note: Would need to create actual PDF for full test
                print("\nNote: Full audit test requires PDF creation")
                print("Sample infractions shown above would be analyzed against uploaded specs")
    else:
        print("No PDF files found in current directory")
        print("Place PG&E spec PDFs here for testing")
    
    print("\n" + "=" * 60)
    print("Test suite complete!")
    print("=" * 60)

if __name__ == "__main__":
    # Allow custom URL via command line
    if len(sys.argv) > 1:
        BASE_URL = sys.argv[1]
        print(f"Using API URL: {BASE_URL}")
    
    main()
