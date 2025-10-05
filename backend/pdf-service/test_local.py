#!/usr/bin/env python3
"""
Test script for local PDF service testing
"""

import requests
import json
from pathlib import Path

# Test configuration
API_BASE = "http://localhost:8000"
SAMPLE_PDF = "../../mobile/assets/sample/PGE AS-BUILT PROCEDURE 2025 (1).pdf"

def test_health():
    """Test health endpoint"""
    resp = requests.get(f"{API_BASE}/health")
    print("Health Check:", resp.json())
    assert resp.status_code == 200

def test_parse_job_pdf():
    """Test job PDF parsing with optimized regex"""
    pdf_path = Path(SAMPLE_PDF)
    
    if not pdf_path.exists():
        print(f"Sample PDF not found at {pdf_path}")
        return
    
    with open(pdf_path, 'rb') as f:
        files = {'job_file': ('test.pdf', f, 'application/pdf')}
        resp = requests.post(f"{API_BASE}/parse-job-pdf/", files=files)
    
    if resp.status_code == 200:
        data = resp.json()
        print("\n=== PDF Parsing Results (Optimized) ===")
        print(f"Success: {data.get('success')}")
        print(f"Total Pages: {data.get('total_pages')}")
        print(f"Total Chunks: {data.get('total_chunks')}")
        
        # Required documents (dynamically extracted)
        required_docs = data.get('required_docs', [])
        if required_docs:
            print(f"\nDynamically Extracted Required Documents: {len(required_docs)}")
            for i, doc in enumerate(required_docs[:10], 1):
                print(f"  {i}. {doc}")
        
        # Materials
        materials = data.get('materials', {})
        if materials.get('headers'):
            print(f"\nMaterials Table (Enhanced):")
            print(f"  Headers: {materials['headers']}")
            print(f"  Rows: {len(materials.get('rows', []))} items")
            if materials.get('rows'):
                for i, row in enumerate(materials['rows'][:5], 1):
                    print(f"    {i}. {row}")
        
        # Instructions
        instructions = data.get('instructions', [])
        if instructions:
            print(f"\nInstructions (Multi-line Support): {len(instructions)} items")
            for i, inst in enumerate(instructions[:5], 1):
                # Show first 80 chars to see multi-line handling
                preview = inst[:80] + "..." if len(inst) > 80 else inst
                print(f"  {i}. {preview}")
        
        # GPS
        gps_links = data.get('gps_links', [])
        if gps_links:
            print(f"\nGPS Locations: {len(gps_links)}")
            for gps in gps_links[:3]:
                print(f"  - {gps['label']}: {gps['coordinates']}")
                if gps.get('context'):
                    print(f"    Context: {gps['context'][:60]}...")
        
        # Documents comparison
        print(f"\nFound Documents: {len(data.get('found_docs', []))}")
        print(f"Missing Documents: {data.get('missing_docs', [])[:5]}")
        
        # Permits
        permits = data.get('permits', [])
        if permits:
            print(f"\nPermits: {permits[:5]}")
    else:
        print(f"Error: {resp.status_code}")
        print(resp.text)

def test_learn_spec():
    """Test spec learning endpoint with embeddings"""
    pdf_path = Path(SAMPLE_PDF)
    
    if not pdf_path.exists():
        print(f"Sample PDF not found at {pdf_path}")
        return
    
    with open(pdf_path, 'rb') as f:
        files = {'spec_file': ('spec.pdf', f, 'application/pdf')}
        resp = requests.post(f"{API_BASE}/learn-spec/", files=files)
    
    if resp.status_code == 200:
        data = resp.json()
        print("\n=== Spec Learning Results ===")
        print(f"Success: {data.get('success')}")
        print(f"Total Chunks: {data.get('total_chunks')}")
        print(f"Total Pages: {data.get('total_pages')}")
        print(f"Index Size: {data.get('index_size')}")
        print(f"Embedding Dimension: {data.get('embedding_dim')}")
        print(f"Message: {data.get('message')}")
        
        return True  # Success
    else:
        print(f"Error: {resp.status_code}")
        print(resp.text)
        return False

def test_analyze_audit():
    """Test audit analysis for infractions"""
    # Create a simple test audit with infractions
    audit_content = """
    AUDIT REPORT
    
    Go-back Infraction: Missing safety barriers at pole location
    
    Violation: Incorrect wire gauge used (14 AWG instead of 12 AWG)
    
    Issue: Failed to install proper grounding as per specification
    
    Problem: Insufficient clearance between conductors (found 3 feet, required 4 feet)
    
    Non-compliance: No permit documentation provided for work performed
    """
    
    # Save as temporary PDF (using reportlab or similar would be needed for real PDF)
    # For testing, we'll use a text file
    import tempfile
    
    with tempfile.NamedTemporaryFile(suffix='.txt', delete=False) as tmp:
        tmp.write(audit_content.encode())
        tmp_path = tmp.name
    
    try:
        # First ensure spec is learned
        spec_learned = test_learn_spec()
        
        if spec_learned:
            print("\n=== Analyzing Audit ===")
            
            # In production, this would be a PDF
            # For now, let's test with the sample PDF as an audit
            with open(Path(SAMPLE_PDF), 'rb') as f:
                files = {'audit_file': ('audit.pdf', f, 'application/pdf')}
                resp = requests.post(f"{API_BASE}/analyze-audit/", files=files)
            
            if resp.status_code == 200:
                data = resp.json()
                print(f"Success: {data.get('success')}")
                
                summary = data.get('summary', {})
                print(f"\n=== Summary ===")
                print(f"Total Infractions: {summary.get('total_infractions')}")
                print(f"Repealable: {summary.get('repealable_count')}")
                print(f"Non-Repealable: {summary.get('non_repealable_count')}")
                print(f"Average Confidence: {summary.get('average_confidence')}%")
                print(f"Spec Chunks Searched: {summary.get('spec_chunks_searched')}")
                
                analysis = data.get('analysis', [])
                if analysis:
                    print(f"\n=== Infraction Analysis (First 3) ===")
                    for i, result in enumerate(analysis[:3], 1):
                        print(f"\n{i}. Infraction: {result['infraction'][:100]}...")
                        print(f"   Repealable: {result['repealable']}")
                        print(f"   Confidence: {result['confidence']}%")
                        
                        if result.get('reasons'):
                            print(f"   Top Reason: {result['reasons'][0]['text'][:150]}...")
            else:
                print(f"Error: {resp.status_code}")
                print(resp.text)
    finally:
        # Clean up temp file
        if 'tmp_path' in locals():
            import os
            os.unlink(tmp_path)

if __name__ == "__main__":
    print("Testing PDF Processing & Analysis Service\n")
    
    try:
        test_health()
        print("✓ Health check passed\n")
        
        print("=" * 60)
        print("Testing Basic PDF Parsing...")
        test_parse_job_pdf()
        
        print("\n" + "=" * 60)
        print("Testing Spec Learning & Audit Analysis...")
        test_analyze_audit()  # This also tests learn_spec
        
        print("\n✓ All tests completed!")
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to service. Make sure it's running:")
        print("   pip install -r requirements.txt")
        print("   uvicorn app:app --host 0.0.0.0 --port 8000 --reload")
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
