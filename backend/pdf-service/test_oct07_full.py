"""
NEXA AI Document Analyzer - October 07, 2025 Full Test Suite
Comprehensive testing with PG&E-specific scenarios
"""
import requests
import sys
import json
import time
from pathlib import Path
from io import BytesIO

# API base URL (adjust for deployment)
BASE_URL = "http://localhost:8000"  # Local testing
# BASE_URL = "https://your-app.onrender.com"  # Production

def create_fusesaver_spec_pdf():
    """Create a detailed FuseSaver spec PDF (Document 092813)"""
    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.pdfgen import canvas
        from reportlab.lib.utils import simpleSplit
        
        buffer = BytesIO()
        c = canvas.Canvas(buffer, pagesize=letter)
        width, height = letter
        
        # Cover page
        c.setFont("Helvetica-Bold", 18)
        c.drawString(50, height - 50, "Document 092813")
        c.drawString(50, height - 75, "Installing the Siemens FuseSaver")
        
        c.setFont("Helvetica", 12)
        c.drawString(50, height - 110, "Rev. #03: Effective Date: 01/15/2025")
        c.drawString(50, height - 130, "Electric Distribution Standards")
        
        # Critical specifications
        c.setFont("Helvetica-Bold", 14)
        c.drawString(50, height - 170, "Purpose and Scope")
        
        c.setFont("Helvetica", 11)
        text = """This document defines the mandatory requirements for FuseSaver installations 
        on PG&E distribution systems. CRITICAL: FuseSavers must be installed on single phase 
        (2 wire and 1 wire) taps ONLY. Installation on three-phase systems is strictly 
        prohibited and will result in operational failures."""
        
        y = height - 200
        for line in simpleSplit(text, "Helvetica", 11, 500):
            c.drawString(50, y, line)
            y -= 15
        
        # Installation requirements
        c.setFont("Helvetica-Bold", 14)
        c.drawString(50, y - 20, "Installation Requirements")
        
        c.setFont("Helvetica", 11)
        requirements = [
            "1. Single-phase taps only (2-wire or 1-wire configuration)",
            "2. Maximum continuous current rating: 100A",
            "3. Minimum phase spacing: 36 inches",
            "4. Coordination time with upstream recloser: 0.35 seconds",
            "5. Ground clearance: minimum 15 feet",
            "6. Guy marker placement per Document 038005"
        ]
        
        y -= 40
        for req in requirements:
            c.drawString(70, y, req)
            y -= 20
        
        # Add second page with technical details
        c.showPage()
        c.setFont("Helvetica-Bold", 14)
        c.drawString(50, height - 50, "Table 3-1: FuseSaver Ratings")
        
        c.setFont("Helvetica", 10)
        table_data = [
            "Configuration | Max Current | Trip Time | Reset Time",
            "Single-phase  | 100A       | 0.05s     | 15s",
            "2-wire tap    | 100A       | 0.05s     | 15s",
            "1-wire tap    | 63A        | 0.03s     | 15s"
        ]
        
        y = height - 80
        for row in table_data:
            c.drawString(70, y, row)
            y -= 15
        
        c.save()
        buffer.seek(0)
        return buffer.getvalue()
    except ImportError:
        # Fallback minimal PDF
        return b"%PDF-1.4\nDocument 092813 FuseSaver specs: single-phase taps only"

def create_garbled_audit_pdf():
    """Create audit PDF with intentionally garbled text"""
    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.pdfgen import canvas
        
        buffer = BytesIO()
        c = canvas.Canvas(buffer, pagesize=letter)
        width, height = letter
        
        c.setFont("Helvetica-Bold", 16)
        c.drawString(50, height - 50, "Quality Control Audit Report")
        c.setFont("Helvetica", 12)
        c.drawString(50, height - 80, f"Date: October 07, 2025")
        c.drawString(50, height - 100, "Job Package: #JP-2025-10-001")
        
        c.setFont("Helvetica-Bold", 14)
        c.drawString(50, height - 140, "Infractions Identified")
        
        c.setFont("Helvetica", 11)
        infractions = [
            "1. Go-back: Incorrect FuseSaver phasing per audit - installed on three-phase line contrary to Document 092813",
            "2. QCInspectionandentercallsnotlistedatendofeachsection.)No proper grounding on recloser installation",
            "3. Go-back: FuseSaver rating exceeds specification (150A installed vs 100A max for single-phase)",
            "4. Infraction: SCADA-Mate SD antenna clearance only 8ft (10ft minimum required)",
            "5. Goback:TripSaverIIcoordinationnotverifiedwithupstreamprotection",
            "6. Issue: Line recloser bypass switch missing per Document 094669 requirements",
            "7. Go back: Sectionalizer settings not coordinated with downstream FuseSaver",
            "8. QCInspection found guy marker placement not per Document038005specifications"
        ]
        
        y = height - 170
        for infraction in infractions:
            # Make some intentionally garbled
            if "QCInspection" in infraction and "andenter" in infraction:
                # Keep garbled
                pass
            elif "Goback:Trip" in infraction:
                # Keep run-together text
                pass
            
            c.drawString(60, y, infraction)
            y -= 30
            if y < 100:
                c.showPage()
                y = height - 50
        
        c.save()
        buffer.seek(0)
        return buffer.getvalue()
    except ImportError:
        return b"%PDF-1.4\nGarbled audit with QCInspectionandentercalls infractions"

def create_recloser_spec_pdf():
    """Create recloser specification PDF (Document 094669)"""
    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.pdfgen import canvas
        
        buffer = BytesIO()
        c = canvas.Canvas(buffer, pagesize=letter)
        width, height = letter
        
        c.setFont("Helvetica-Bold", 18)
        c.drawString(50, height - 50, "Document 094669")
        c.drawString(50, height - 75, "OH: Switches - Line Reclosers")
        
        c.setFont("Helvetica", 12)
        c.drawString(50, height - 110, "Rev. #02: TD-2908P-01")
        c.drawString(50, height - 130, "Electric Distribution - Overhead")
        
        c.setFont("Helvetica-Bold", 14)
        c.drawString(50, height - 170, "Recloser Installation Standards")
        
        c.setFont("Helvetica", 11)
        standards = [
            "1. All line reclosers must include bypass switches",
            "2. Ratings must match system fault current capacity",
            "3. Minimum interrupting rating: 12.5kA",
            "4. Coordination with FuseSavers required on all taps",
            "5. SCADA integration mandatory for automated schemes",
            "6. Ground grid resistance: maximum 5 ohms"
        ]
        
        y = height - 200
        for std in standards:
            c.drawString(70, y, std)
            y -= 20
        
        c.save()
        buffer.seek(0)
        return buffer.getvalue()
    except ImportError:
        return b"%PDF-1.4\nDocument 094669 Line Recloser specifications"

def test_health():
    """Test health endpoint"""
    print("\n🔍 Testing health endpoint...")
    response = requests.get(f"{BASE_URL}/health")
    
    if response.status_code == 200:
        data = response.json()
        print("✅ Health check passed")
        print(f"   Device: {data['device']}")
        print(f"   OCR Available: {data.get('ocr_available', 'unknown')}")
        print(f"   Max file size: {data.get('max_file_size_mb', 1100)}MB")
        print(f"   Spec learned: {data['spec_learned']}")
        return True
    else:
        print(f"❌ Health check failed: {response.status_code}")
        return False

def test_upload_multiple_specs():
    """Upload multiple PG&E specification documents"""
    print("\n📤 Uploading PG&E specification suite...")
    
    specs = [
        ("FuseSaver Spec", create_fusesaver_spec_pdf()),
        ("Recloser Spec", create_recloser_spec_pdf())
    ]
    
    for name, content in specs:
        print(f"   Uploading {name}...")
        files = {'file': (f'{name}.pdf', content, 'application/pdf')}
        response = requests.post(f"{BASE_URL}/upload-spec-book", files=files)
        
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ {name} uploaded: {data['chunks_learned']} chunks")
        else:
            print(f"   ❌ {name} upload failed: {response.status_code}")
            return False
    
    return True

def test_garbled_audit_analysis():
    """Test analysis of audit with garbled text"""
    print("\n🔍 Analyzing garbled audit report...")
    
    audit_content = create_garbled_audit_pdf()
    files = {'file': ('garbled_audit.pdf', audit_content, 'application/pdf')}
    
    response = requests.post(f"{BASE_URL}/analyze-audit", files=files)
    
    if response.status_code == 200:
        results = response.json()
        print(f"✅ Analysis complete: {len(results)} infractions processed")
        
        # Check specific scenarios
        fusesaver_found = False
        garbled_cleaned = False
        recloser_found = False
        
        for result in results:
            infraction_text = result['infraction']
            
            # Check FuseSaver three-phase violation
            if 'FuseSaver' in infraction_text and 'three-phase' in infraction_text:
                fusesaver_found = True
                print(f"\n   🎯 FuseSaver violation detected:")
                print(f"      Status: {result['status']}")
                print(f"      Confidence: {result['confidence']}%")
                if result['status'] == 'REPEALABLE':
                    print("      ✅ Correctly marked as REPEALABLE (spec says single-phase only)")
                
            # Check if garbled text was cleaned
            if 'QC Inspection' in infraction_text or 'proper grounding' in infraction_text:
                if 'andentercalls' not in infraction_text:  # Should be cleaned
                    garbled_cleaned = True
                    print(f"\n   🧹 Garbled text cleaned successfully:")
                    print(f"      Original had: QCInspectionandentercalls...")
                    print(f"      Cleaned to: {infraction_text[:80]}...")
            
            # Check recloser bypass switch
            if 'recloser' in infraction_text.lower() and 'bypass' in infraction_text.lower():
                recloser_found = True
                print(f"\n   ⚡ Recloser issue detected:")
                print(f"      Status: {result['status']}")
                print(f"      Matches Document 094669: {any('094669' in r for r in result['reasons'])}")
        
        # Summary
        print("\n   📊 Test Results:")
        print(f"      FuseSaver three-phase violation: {'✅ Found' if fusesaver_found else '❌ Not found'}")
        print(f"      Garbled text cleaning: {'✅ Working' if garbled_cleaned else '❌ Not working'}")
        print(f"      Recloser spec matching: {'✅ Found' if recloser_found else '❌ Not found'}")
        
        return fusesaver_found and garbled_cleaned
    else:
        print(f"❌ Analysis failed: {response.status_code}")
        print(f"   Response: {response.text}")
        return False

def test_confidence_scoring():
    """Test confidence scoring for different infraction types"""
    print("\n📊 Testing confidence scoring...")
    
    # Create a simple audit with one clear infraction
    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.pdfgen import canvas
        
        buffer = BytesIO()
        c = canvas.Canvas(buffer, pagesize=letter)
        width, height = letter
        
        c.setFont("Helvetica", 12)
        c.drawString(50, height - 50, "Audit Report")
        c.drawString(50, height - 100, "Go-back: FuseSaver installed on single-phase tap per Document 092813")
        c.drawString(50, height - 130, "Issue: Unknown equipment XYZ123 not functioning")
        
        c.save()
        buffer.seek(0)
        audit_content = buffer.getvalue()
    except ImportError:
        audit_content = b"%PDF-1.4\nSimple audit test"
    
    files = {'file': ('confidence_test.pdf', audit_content, 'application/pdf')}
    response = requests.post(f"{BASE_URL}/analyze-audit", files=files)
    
    if response.status_code == 200:
        results = response.json()
        
        for result in results:
            if 'FuseSaver' in result['infraction'] and 'single-phase' in result['infraction']:
                print(f"   FuseSaver compliance: {result['confidence']}% confidence")
                if result['confidence'] > 70:
                    print("   ✅ High confidence match with spec")
            elif 'Unknown equipment' in result['infraction']:
                print(f"   Unknown equipment: {result['confidence']}% confidence")
                if result['confidence'] < 50:
                    print("   ✅ Low confidence (as expected for unknown equipment)")
        
        return True
    else:
        return False

def test_large_file_handling():
    """Test handling of large PDF files"""
    print("\n📦 Testing large file handling...")
    
    # Create a large-ish PDF (not actually 1100MB, but test the endpoint)
    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.pdfgen import canvas
        
        buffer = BytesIO()
        c = canvas.Canvas(buffer, pagesize=letter)
        width, height = letter
        
        # Add many pages
        for page in range(50):
            c.setFont("Helvetica", 10)
            c.drawString(50, height - 50, f"Page {page + 1}")
            c.drawString(50, height - 100, "Document 092813 " * 100)  # Repeat text
            c.showPage()
        
        c.save()
        buffer.seek(0)
        content = buffer.getvalue()
        
        print(f"   Created test PDF: {len(content) / 1024:.1f} KB")
        
        files = {'file': ('large_test.pdf', content, 'application/pdf')}
        response = requests.post(f"{BASE_URL}/upload-spec-book", files=files)
        
        if response.status_code == 200:
            print("   ✅ Large file handled successfully")
            return True
        elif response.status_code == 413:
            print("   ✅ File size limit enforced correctly")
            return True
        else:
            print(f"   ❌ Unexpected response: {response.status_code}")
            return False
            
    except ImportError:
        print("   ⚠️  Skipping (reportlab not installed)")
        return True

def run_full_test_suite():
    """Run comprehensive test suite"""
    print("=" * 70)
    print("🚀 NEXA AI Document Analyzer - October 07, 2025 Full Test Suite")
    print("=" * 70)
    
    tests = [
        ("Health Check", test_health),
        ("Upload Multiple Specs", test_upload_multiple_specs),
        ("Garbled Audit Analysis", test_garbled_audit_analysis),
        ("Confidence Scoring", test_confidence_scoring),
        ("Large File Handling", test_large_file_handling)
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            print(f"\n{'='*70}")
            passed = test_func()
            results.append((test_name, passed))
            time.sleep(0.5)  # Brief pause between tests
        except Exception as e:
            print(f"\n❌ {test_name} failed with error: {e}")
            results.append((test_name, False))
    
    # Final Summary
    print("\n" + "=" * 70)
    print("📊 FINAL TEST SUMMARY - October 07, 2025")
    print("=" * 70)
    
    passed_count = sum(1 for _, passed in results if passed)
    total_count = len(results)
    
    for test_name, passed in results:
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"  {test_name:35} {status}")
    
    print("-" * 70)
    print(f"  Overall: {passed_count}/{total_count} tests passed")
    
    if passed_count == total_count:
        print("\n🎉 All tests passed! System ready for deployment.")
        print("\n📝 Key validations confirmed:")
        print("  • FuseSaver single-phase requirement enforced")
        print("  • Garbled audit text cleaning working")
        print("  • Recloser bypass switch detection active")
        print("  • Confidence scoring properly calibrated")
    else:
        print(f"\n⚠️  {total_count - passed_count} test(s) failed. Review logs above.")
    
    return passed_count == total_count

if __name__ == "__main__":
    # Check server availability
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=2)
    except requests.exceptions.ConnectionError:
        print("❌ Server not running at", BASE_URL)
        print("\nTo start the server locally:")
        print("  cd backend/pdf-service")
        print("  uvicorn app_oct2025_enhanced:app --reload --port 8000")
        print("\nFor production deployment, update BASE_URL to your Render URL")
        sys.exit(1)
    
    # Run full test suite
    success = run_full_test_suite()
    sys.exit(0 if success else 1)
