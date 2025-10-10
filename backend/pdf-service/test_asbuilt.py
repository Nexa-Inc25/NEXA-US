"""
Test suite for PG&E As-Built Processing
Tests the complete workflow from procedure learning to as-built filling
"""
import requests
import json
import time
import base64
from pathlib import Path

# Configuration
BASE_URL = "https://nexa-doc-analyzer-oct2025.onrender.com"
LOCAL_URL = "http://localhost:8000"

# Use production by default
API_URL = BASE_URL

def test_asbuilt_workflow():
    """Complete workflow test"""
    print("=" * 50)
    print("🧪 PG&E As-Built Processing Test Suite")
    print("=" * 50)
    
    results = {}
    
    # Test 1: Health check
    print("\n1️⃣ Testing API health...")
    try:
        r = requests.get(f"{API_URL}/health", timeout=5)
        if r.status_code == 200:
            print("✅ API is healthy")
            results['health'] = True
        else:
            print(f"❌ API unhealthy: {r.status_code}")
            results['health'] = False
    except Exception as e:
        print(f"❌ API unreachable: {e}")
        results['health'] = False
    
    # Test 2: Queue status (verify Celery)
    print("\n2️⃣ Testing Celery workers...")
    try:
        r = requests.get(f"{API_URL}/queue-status", timeout=5)
        data = r.json()
        if data.get('workers', {}).get('available'):
            print(f"✅ Celery workers available: {data['workers']['count']}")
            results['celery'] = True
        else:
            print("❌ No Celery workers available")
            results['celery'] = False
    except Exception as e:
        print(f"❌ Queue check failed: {e}")
        results['celery'] = False
    
    # Test 3: Create sample as-built PDF
    print("\n3️⃣ Creating test as-built PDF...")
    test_pdf = create_test_asbuilt()
    print("✅ Test PDF created")
    
    # Test 4: Submit as-built for processing
    print("\n4️⃣ Submitting as-built for processing...")
    try:
        files = {"file": ("test_asbuilt.pdf", test_pdf, "application/pdf")}
        data = {
            "pm_number": "TEST-07D",
            "notification_number": "TEST-12345",
            "work_type": "Planned Estimated"
        }
        
        r = requests.post(f"{API_URL}/asbuilt/fill-async", files=files, data=data)
        
        if r.status_code == 200:
            job_data = r.json()
            job_id = job_data['job_id']
            print(f"✅ Job submitted: {job_id}")
            results['submit'] = True
            
            # Test 5: Poll for results
            print("\n5️⃣ Processing as-built...")
            for i in range(15):  # Poll for up to 30 seconds
                time.sleep(2)
                r2 = requests.get(f"{API_URL}/asbuilt/result/{job_id}")
                result = r2.json()
                
                status = result.get('status', 'unknown')
                print(f"   Status: {status}", end="")
                
                if status == 'processing':
                    progress = result.get('progress', 0)
                    print(f" ({progress}%)")
                elif status == 'complete':
                    print("\n✅ As-built processed successfully!")
                    results['process'] = True
                    
                    # Display results
                    if 'result' in result:
                        res = result['result']
                        print(f"\n📊 Results:")
                        print(f"   Work Type: {res.get('work_type', 'N/A')}")
                        print(f"   Compliance: {res.get('compliance_score', 0):.1f}%")
                        print(f"   Required Docs: {len(res.get('required_docs', []))}")
                        print(f"   Materials: {len(res.get('mat_codes', []))}")
                        
                        if 'pricing' in res:
                            print(f"   Total Price: ${res['pricing'].get('total', 0):.2f}")
                        
                        if 'fill_suggestions' in res:
                            red = len(res['fill_suggestions'].get('red_line', []))
                            blue = len(res['fill_suggestions'].get('blue_line', []))
                            print(f"   Suggestions: {red} red-line, {blue} blue-line")
                    break
                elif status == 'failed':
                    print(f"\n❌ Processing failed: {result.get('error', 'Unknown')}")
                    results['process'] = False
                    break
                else:
                    print()
            else:
                print("\n⏱️ Processing timeout")
                results['process'] = False
                
        else:
            print(f"❌ Submit failed: {r.status_code}")
            print(f"   Response: {r.text[:200]}")
            results['submit'] = False
            
    except Exception as e:
        print(f"❌ Submit error: {e}")
        results['submit'] = False
    
    # Test 6: Material price update
    print("\n6️⃣ Testing material price update...")
    try:
        test_prices = {"TEST-A": 100.00, "TEST-B": 200.00, "TEST-Z": 50.00}
        files = {
            "file": (
                "test_prices.json",
                json.dumps(test_prices).encode(),
                "application/json"
            )
        }
        
        r = requests.post(f"{API_URL}/asbuilt/update-mat-prices", files=files)
        
        if r.status_code == 200:
            print(f"✅ Material prices updated: {len(test_prices)} items")
            results['prices'] = True
        else:
            print(f"❌ Price update failed: {r.status_code}")
            results['prices'] = False
            
    except Exception as e:
        print(f"❌ Price update error: {e}")
        results['prices'] = False
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 TEST SUMMARY")
    print("=" * 50)
    
    tests_passed = sum(1 for v in results.values() if v)
    total_tests = len(results)
    
    for test_name, passed in results.items():
        status = "✅" if passed else "❌"
        print(f"{test_name:.<20} {status}")
    
    print("\n" + "=" * 50)
    print(f"Results: {tests_passed}/{total_tests} tests passed")
    
    if tests_passed == total_tests:
        print("🎉 All tests passed! As-built processing ready!")
    else:
        print("⚠️ Some tests failed. Check configuration.")
    
    return results


def create_test_asbuilt():
    """Create a simple test PDF with as-built content"""
    # Create a minimal PDF with test content
    pdf_content = b"""%PDF-1.4
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
<< /Length 500 >>
stream
BT
/F1 12 Tf
50 750 Td
(PG&E As-Built Test Document) Tj
0 -20 Td
(PM Number: TEST-07D) Tj
0 -20 Td
(Notification: TEST-12345) Tj
0 -20 Td
(Work Type: Planned Estimated) Tj
0 -40 Td
(Materials Used:) Tj
0 -20 Td
(- Mat Z: Pole Hardware Kit) Tj
0 -20 Td
(- Mat A: Transformer 25kVA) Tj
0 -20 Td
(- Mat B: Cross-arm Assembly) Tj
0 -40 Td
(Field Notes:) Tj
0 -20 Td
(- Item X not installed - struck through) Tj
0 -20 Td
(- FIF: Found additional equipment in field) Tj
0 -20 Td
(- FCOA: Field change approved for relocation) Tj
ET
endstream
endobj
xref
0 6
trailer
<< /Size 6 /Root 1 0 R >>
startxref
1234
%%EOF"""
    
    return pdf_content


def test_batch_processing():
    """Test batch as-built processing"""
    print("\n" + "=" * 50)
    print("🔄 Testing Batch Processing")
    print("=" * 50)
    
    # Create multiple test PDFs
    batch_files = []
    job_data_list = []
    
    for i in range(3):
        pdf = create_test_asbuilt()
        batch_files.append((
            'files',
            (f'test_{i+1}.pdf', pdf, 'application/pdf')
        ))
        job_data_list.append({
            'pm_number': f'TEST-{i+1:03d}',
            'notification_number': f'NOTIF-{i+1:05d}',
            'work_type': 'Planned Estimated'
        })
    
    # Submit batch
    try:
        data = {
            'job_data_json': json.dumps(job_data_list)
        }
        
        r = requests.post(
            f"{API_URL}/asbuilt/batch-fill",
            files=batch_files,
            data=data
        )
        
        if r.status_code == 200:
            batch_data = r.json()
            batch_id = batch_data['batch_id']
            print(f"✅ Batch submitted: {batch_id}")
            print(f"   Files: {batch_data['total_files']}")
            
            # Poll for results
            print("\n⏳ Processing batch...")
            for i in range(20):
                time.sleep(3)
                r2 = requests.get(f"{API_URL}/asbuilt/batch-result/{batch_id}")
                result = r2.json()
                
                status = result.get('status')
                if status == 'processing':
                    progress = result.get('progress', 0)
                    current = result.get('current', 'Unknown')
                    print(f"   Progress: {progress}% - Processing {current}")
                elif status == 'complete':
                    print("\n✅ Batch completed!")
                    summary = result.get('summary', {})
                    print(f"   Total Pricing: ${summary.get('total_pricing', 0):.2f}")
                    print(f"   Avg Compliance: {summary.get('avg_compliance', 0):.1f}%")
                    
                    if 'results' in result:
                        print(f"   Successful: {len(result['results'])}")
                    if 'errors' in result:
                        print(f"   Failed: {len(result['errors'])}")
                    
                    return True
                elif status == 'failed':
                    print(f"\n❌ Batch failed: {result.get('error')}")
                    return False
            
            print("\n⏱️ Batch timeout")
            return False
            
        else:
            print(f"❌ Batch submit failed: {r.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Batch error: {e}")
        return False


def test_compliance_check(job_id: str):
    """Test compliance checking"""
    try:
        r = requests.get(f"{API_URL}/asbuilt/compliance-check/{job_id}")
        if r.status_code == 200:
            data = r.json()
            print(f"\n📋 Compliance Check:")
            print(f"   Score: {data['compliance_score']}%")
            print(f"   Level: {data['level']}")
            print(f"   Required Docs: {len(data['required_docs'])}")
            print(f"   Pricing: ${data['pricing']:.2f}")
            return True
        else:
            print(f"❌ Compliance check failed: {r.status_code}")
            return False
    except Exception as e:
        print(f"❌ Compliance error: {e}")
        return False


if __name__ == "__main__":
    # Run main workflow test
    results = test_asbuilt_workflow()
    
    # Run batch test if single processing worked
    if results.get('process'):
        print("\n" + "=" * 50)
        batch_success = test_batch_processing()
        if batch_success:
            print("✅ Batch processing working!")
        else:
            print("❌ Batch processing failed")
    
    print("\n🏁 Testing complete!")
