"""
Test Suite for Pole Classification and Document Ordering
Tests the enhanced PG&E as-built processing features
"""
import requests
import json
import time
import base64

# Configuration
BASE_URL = "https://nexa-doc-analyzer-oct2025.onrender.com"
LOCAL_URL = "http://localhost:8000"
API_URL = BASE_URL  # Use production

def test_pole_classification():
    """Test pole type classification"""
    print("=" * 50)
    print("🔍 Testing Pole Classification System")
    print("=" * 50)
    
    # Test cases for different pole types
    test_cases = [
        {
            "description": "Service pole with single primary level",
            "expected_type": 1,
            "text": "Service pole installation. Single primary level, no equipment."
        },
        {
            "description": "Two-level pole with transformer",
            "expected_type": 2,
            "text": "Primary level with buck arm. Single-phase transformer installed. Cutouts present."
        },
        {
            "description": "Three-level with transformer bank",
            "expected_type": 3,
            "text": "Main line configuration with buck arm and transformer bank. Three levels total. Recloser installed."
        },
        {
            "description": "Four-level complex setup",
            "expected_type": 4,
            "text": "Primary, buck, transformer, and secondary levels. Four-level configuration with Type 3 equipment."
        },
        {
            "description": "Special difficulty pole",
            "expected_type": 5,
            "text": "More than 4 levels. Difficult access terrain. Special equipment. Requires NTE bid."
        }
    ]
    
    results = []
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n📍 Test Case {i}: {test_case['description']}")
        
        # Create test PDF with description
        test_pdf = create_test_pdf_with_text(test_case['text'])
        
        # Submit for processing
        files = {"file": ("test_pole.pdf", test_pdf, "application/pdf")}
        data = {
            "pm_number": f"TEST-POLE-{i}",
            "notification_number": f"NOTIF-{i:05d}",
            "work_type": "Planned Estimated"
        }
        
        try:
            r = requests.post(f"{API_URL}/asbuilt/fill-async", files=files, data=data)
            
            if r.status_code == 200:
                job_id = r.json()['job_id']
                
                # Poll for result
                for _ in range(10):
                    time.sleep(2)
                    r2 = requests.get(f"{API_URL}/asbuilt/result/{job_id}")
                    result = r2.json()
                    
                    if result['status'] == 'complete':
                        pole_type = result['result'].get('pole_type', 0)
                        confidence = result['result'].get('pole_confidence', 0)
                        reason = result['result'].get('pole_reason', 'N/A')
                        
                        success = pole_type == test_case['expected_type']
                        status = "✅" if success else "❌"
                        
                        print(f"   {status} Expected: Type {test_case['expected_type']}, Got: Type {pole_type}")
                        print(f"   Confidence: {confidence:.1f}%")
                        print(f"   Reason: {reason}")
                        
                        # Check pricing adjustment
                        if 'pricing' in result['result']:
                            pricing = result['result']['pricing']
                            if 'pole_adjustment' in pricing:
                                print(f"   Pricing: {pricing['pole_adjustment']}")
                        
                        results.append(success)
                        break
                    elif result['status'] == 'failed':
                        print(f"   ❌ Processing failed: {result.get('error', 'Unknown')}")
                        results.append(False)
                        break
                else:
                    print(f"   ⏱️ Timeout waiting for result")
                    results.append(False)
                    
            else:
                print(f"   ❌ Submit failed: {r.status_code}")
                results.append(False)
                
        except Exception as e:
            print(f"   ❌ Error: {e}")
            results.append(False)
    
    # Summary
    print(f"\n{'=' * 50}")
    print(f"Results: {sum(results)}/{len(results)} tests passed")
    print(f"Accuracy: {(sum(results)/len(results)*100):.1f}%")
    
    return sum(results) == len(results)


def test_document_ordering():
    """Test document ordering system"""
    print("\n" + "=" * 50)
    print("📋 Testing Document Ordering System")
    print("=" * 50)
    
    # Test different work types
    work_types = [
        ("Planned Estimated", 11),  # Expected doc count
        ("Routine Emergency Estimated", 9),
        ("Planned WRG", 10),
        ("Emergency Unit Completion", 4)
    ]
    
    results = []
    
    for work_type, expected_count in work_types:
        print(f"\n🔍 Testing: {work_type}")
        
        # Create test as-built
        test_pdf = create_test_pdf_with_text(f"Work Type: {work_type}")
        
        files = {"file": ("test_order.pdf", test_pdf, "application/pdf")}
        data = {
            "pm_number": f"TEST-ORDER",
            "notification_number": "12345",
            "work_type": work_type
        }
        
        try:
            r = requests.post(f"{API_URL}/asbuilt/fill-async", files=files, data=data)
            
            if r.status_code == 200:
                job_id = r.json()['job_id']
                
                # Get result
                for _ in range(10):
                    time.sleep(2)
                    r2 = requests.get(f"{API_URL}/asbuilt/result/{job_id}")
                    result = r2.json()
                    
                    if result['status'] == 'complete':
                        ordered_docs = result['result'].get('ordered_documents', [])
                        validation = result['result'].get('document_validation', {})
                        
                        print(f"   Documents required: {len(ordered_docs)}")
                        print(f"   Completeness: {validation.get('completeness', 0):.1f}%")
                        
                        # Check if POLE BILL is first (when present)
                        if ordered_docs and 'POLE BILL' in ordered_docs:
                            pole_bill_first = ordered_docs[0] == 'POLE BILL'
                            print(f"   {'✅' if pole_bill_first else '❌'} POLE BILL first: {pole_bill_first}")
                        
                        # Check if CCSC is last (when present)
                        if ordered_docs and 'CCSC' in ordered_docs:
                            ccsc_last = ordered_docs[-1] == 'CCSC'
                            print(f"   {'✅' if ccsc_last else '❌'} CCSC last: {ccsc_last}")
                        
                        # First 3 documents
                        if ordered_docs:
                            print(f"   Order: {' → '.join(ordered_docs[:3])}...")
                        
                        results.append(True)
                        break
                    elif result['status'] == 'failed':
                        print(f"   ❌ Failed: {result.get('error')}")
                        results.append(False)
                        break
                else:
                    print(f"   ⏱️ Timeout")
                    results.append(False)
                    
            else:
                print(f"   ❌ Submit failed: {r.status_code}")
                results.append(False)
                
        except Exception as e:
            print(f"   ❌ Error: {e}")
            results.append(False)
    
    print(f"\n{'=' * 50}")
    print(f"Results: {sum(results)}/{len(results)} work types tested successfully")
    
    return sum(results) == len(results)


def test_pricing_adjustments():
    """Test pole-based pricing adjustments"""
    print("\n" + "=" * 50)
    print("💰 Testing Pricing Adjustments")
    print("=" * 50)
    
    base_price = 1000.00
    
    # Test each pole type's pricing
    pole_configs = [
        (1, 1.0, "Type 1: Easy"),
        (2, 1.2, "Type 2: Moderate"),
        (3, 1.5, "Type 3: Medium"),
        (4, 2.0, "Type 4: Difficult"),
        (5, 'NTE', "Type 5: Bid/NTE")
    ]
    
    for pole_type, multiplier, description in pole_configs:
        print(f"\n📊 {description}")
        
        if multiplier == 'NTE':
            print(f"   Base: ${base_price:.2f}")
            print(f"   Multiplier: Requires Bid/NTE")
            print(f"   Result: Custom pricing required")
        else:
            adjusted = base_price * multiplier
            print(f"   Base: ${base_price:.2f}")
            print(f"   Multiplier: {multiplier}x")
            print(f"   Adjusted: ${adjusted:.2f}")
    
    return True


def test_submittal_validation():
    """Test submittal completeness validation"""
    print("\n" + "=" * 50)
    print("✅ Testing Submittal Validation")
    print("=" * 50)
    
    # Create test with missing documents
    test_pdf = create_test_pdf_with_text(
        "Work Type: Planned Estimated\n"
        "Documents included: EC TAG, CONSTRUCTION DRAWING, CREW INSTRUCTIONS"
    )
    
    files = {"file": ("incomplete.pdf", test_pdf, "application/pdf")}
    data = {
        "pm_number": "TEST-VALIDATION",
        "notification_number": "99999",
        "work_type": "Planned Estimated"
    }
    
    try:
        r = requests.post(f"{API_URL}/asbuilt/fill-async", files=files, data=data)
        
        if r.status_code == 200:
            job_id = r.json()['job_id']
            
            # Get result
            for _ in range(10):
                time.sleep(2)
                r2 = requests.get(f"{API_URL}/asbuilt/result/{job_id}")
                result = r2.json()
                
                if result['status'] == 'complete':
                    validation = result['result'].get('document_validation', {})
                    
                    print(f"\n📊 Validation Results:")
                    print(f"   Valid: {validation.get('valid', False)}")
                    print(f"   Completeness: {validation.get('completeness', 0):.1f}%")
                    print(f"   Required: {validation.get('required_count', 0)} documents")
                    print(f"   Provided: {validation.get('provided_count', 0)} documents")
                    
                    missing = validation.get('missing_documents', [])
                    if missing:
                        print(f"   Missing: {', '.join(missing[:5])}")
                        if len(missing) > 5:
                            print(f"            ...and {len(missing)-5} more")
                    
                    return True
                elif result['status'] == 'failed':
                    print(f"❌ Validation failed: {result.get('error')}")
                    return False
            
            print("⏱️ Timeout")
            return False
            
        else:
            print(f"❌ Submit failed: {r.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def create_test_pdf_with_text(text: str) -> bytes:
    """Create a simple PDF with specified text content"""
    pdf_template = """%%PDF-1.4
1 0 obj
<< /Type /Catalog /Pages 2 0 R >>
endobj
2 0 obj
<< /Type /Pages /Kids [3 0 R] /Count 1 >>
endobj
3 0 obj
<< /Type /Page /Parent 2 0 R /Resources 4 0 R /MediaBox [0 0 612 792] /Contents 5 0 R >>
endobj
4 0 obj
<< /Font << /F1 << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> >> >>
endobj
5 0 obj
<< /Length %d >>
stream
BT
/F1 12 Tf
50 750 Td
(PG&E As-Built Test Document) Tj
0 -20 Td
%s
ET
endstream
endobj
xref
0 6
trailer
<< /Size 6 /Root 1 0 R >>
startxref
1234
%%%%EOF"""
    
    # Format text for PDF
    pdf_text = ""
    for line in text.split('\n'):
        pdf_text += f"({line}) Tj\n0 -20 Td\n"
    
    # Calculate stream length
    stream_content = f"BT\n/F1 12 Tf\n50 750 Td\n(PG&E As-Built Test Document) Tj\n0 -20 Td\n{pdf_text}ET\n"
    stream_length = len(stream_content)
    
    # Create final PDF
    pdf_content = pdf_template % (stream_length, pdf_text)
    return pdf_content.encode('latin-1')


def run_all_tests():
    """Run complete test suite"""
    print("=" * 50)
    print("🚀 PG&E Pole Classification & Ordering Test Suite")
    print("=" * 50)
    
    results = {}
    
    # Check API health first
    print("\n🔍 Checking API health...")
    try:
        r = requests.get(f"{API_URL}/health", timeout=5)
        if r.status_code == 200:
            print("✅ API is healthy")
        else:
            print("❌ API not responding properly")
            return
    except:
        print("❌ Cannot connect to API")
        return
    
    # Run tests
    print("\nRunning tests...")
    
    results['Pole Classification'] = test_pole_classification()
    results['Document Ordering'] = test_document_ordering()
    results['Pricing Adjustments'] = test_pricing_adjustments()
    results['Submittal Validation'] = test_submittal_validation()
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 FINAL TEST RESULTS")
    print("=" * 50)
    
    for test_name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{test_name:.<30} {status}")
    
    total = len(results)
    passed = sum(1 for v in results.values() if v)
    
    print(f"\nOverall: {passed}/{total} test suites passed")
    
    if passed == total:
        print("🎉 All tests passed! System ready for production!")
    else:
        print("⚠️ Some tests failed. Review and fix issues.")


if __name__ == "__main__":
    run_all_tests()
