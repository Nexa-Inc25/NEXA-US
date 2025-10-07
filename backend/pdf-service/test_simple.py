"""
Simple test for NEXA AI Document Analyzer
Tests basic functionality without complex PDF generation
"""
import requests
import json

BASE_URL = "http://localhost:8000"

def test_api():
    print("=" * 50)
    print("NEXA Document Analyzer - Simple Test")
    print("=" * 50)
    
    # 1. Test root endpoint
    print("\n1. Testing root endpoint...")
    response = requests.get(f"{BASE_URL}/")
    if response.status_code == 200:
        data = response.json()
        print(f"✅ API Running: {data['name']}")
        print(f"   Version: {data['version']}")
        print(f"   Device: {data['device']}")
        print(f"   Features available:")
        for feature in data.get('features', []):
            print(f"     • {feature}")
    else:
        print(f"❌ Failed: {response.status_code}")
        return False
    
    # 2. Test health
    print("\n2. Testing health endpoint...")
    response = requests.get(f"{BASE_URL}/health")
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Health: {data['status']}")
        print(f"   Max file size: {data.get('max_file_size_mb', 1100)}MB")
        print(f"   OCR available: {data.get('ocr_available', False)}")
        print(f"   Spec learned: {data.get('spec_learned', False)}")
    else:
        print(f"❌ Failed: {response.status_code}")
        return False
    
    # 3. Test with simple text PDF
    print("\n3. Creating simple test PDF...")
    
    # Create a minimal PDF with FuseSaver content
    pdf_content = b"""%PDF-1.4
1 0 obj
<< /Type /Catalog /Pages 2 0 R >>
endobj
2 0 obj
<< /Type /Pages /Kids [3 0 R] /Count 1 >>
endobj
3 0 obj
<< /Type /Page /Parent 2 0 R /Resources << /Font << /F1 4 0 R >> >> /MediaBox [0 0 612 792] /Contents 5 0 R >>
endobj
4 0 obj
<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>
endobj
5 0 obj
<< /Length 500 >>
stream
BT
/F1 12 Tf
50 750 Td
(Document 092813 - FuseSaver Installation Requirements) Tj
0 -20 Td
(Rev. #03: Effective Date: 01/15/2025) Tj
0 -20 Td
(CRITICAL: FuseSavers must be installed on single phase taps ONLY.) Tj
0 -20 Td
(Installation on three-phase systems is strictly prohibited.) Tj
0 -20 Td
(Maximum rating: 100A for single-phase applications.) Tj
0 -20 Td
(Coordination with upstream reclosers required.) Tj
ET
endstream
endobj
xref
0 6
0000000000 65535 f
0000000009 00000 n
0000000058 00000 n
0000000115 00000 n
0000000229 00000 n
0000000317 00000 n
trailer
<< /Size 6 /Root 1 0 R >>
startxref
870
%%EOF"""
    
    # Upload as spec
    print("   Uploading FuseSaver spec...")
    files = {'file': ('fusesaver_spec.pdf', pdf_content, 'application/pdf')}
    response = requests.post(f"{BASE_URL}/upload-spec-book", files=files)
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Spec uploaded: {data['chunks_learned']} chunks learned")
    else:
        print(f"❌ Upload failed: {response.status_code}")
        print(f"   Error: {response.text}")
        return False
    
    # 4. Test audit analysis
    print("\n4. Creating audit PDF with infractions...")
    
    audit_pdf = b"""%PDF-1.4
1 0 obj
<< /Type /Catalog /Pages 2 0 R >>
endobj
2 0 obj
<< /Type /Pages /Kids [3 0 R] /Count 1 >>
endobj
3 0 obj
<< /Type /Page /Parent 2 0 R /Resources << /Font << /F1 4 0 R >> >> /MediaBox [0 0 612 792] /Contents 5 0 R >>
endobj
4 0 obj
<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>
endobj
5 0 obj
<< /Length 400 >>
stream
BT
/F1 12 Tf
50 750 Td
(Quality Control Audit Report) Tj
0 -20 Td
(Date: October 07, 2025) Tj
0 -40 Td
(Infractions Found:) Tj
0 -20 Td
(1. Go-back: FuseSaver installed on three-phase line) Tj
0 -20 Td
(2. Issue: FuseSaver rating 150A exceeds spec max 100A) Tj
0 -20 Td
(3. Go-back: No coordination with upstream recloser) Tj
ET
endstream
endobj
xref
0 6
0000000000 65535 f
0000000009 00000 n
0000000058 00000 n
0000000115 00000 n
0000000229 00000 n
0000000317 00000 n
trailer
<< /Size 6 /Root 1 0 R >>
startxref
770
%%EOF"""
    
    print("   Analyzing audit...")
    files = {'file': ('audit.pdf', audit_pdf, 'application/pdf')}
    response = requests.post(f"{BASE_URL}/analyze-audit", files=files)
    
    if response.status_code == 200:
        results = response.json()
        print(f"✅ Analysis complete: {len(results)} infractions found")
        
        for i, result in enumerate(results, 1):
            print(f"\n   Infraction {i}:")
            print(f"     Text: {result['infraction'][:80]}...")
            print(f"     Status: {result['status']}")
            print(f"     Confidence: {result['confidence']}%")
            print(f"     Matches: {result['match_count']}")
            
            # Check if FuseSaver violations are detected
            if 'FuseSaver' in result['infraction']:
                if 'three-phase' in result['infraction']:
                    print("     ✨ Three-phase violation detected!")
                if '150A' in result['infraction']:
                    print("     ✨ Rating violation detected!")
    else:
        print(f"❌ Analysis failed: {response.status_code}")
        print(f"   Error: {response.text}")
        return False
    
    print("\n" + "=" * 50)
    print("✅ All simple tests completed successfully!")
    print("=" * 50)
    return True

if __name__ == "__main__":
    try:
        test_api()
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to server at", BASE_URL)
        print("   Make sure the server is running:")
        print("   python -m uvicorn app_oct2025_enhanced:app --port 8000")
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
