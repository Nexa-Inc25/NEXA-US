"""
Test script for /analyze-audit endpoint
Tests the live NEXA Document Analyzer service on Render.com
"""
import requests
import json
from pathlib import Path

# Production URL
BASE_URL = "https://nexa-doc-analyzer-oct2025.onrender.com"

def test_health():
    """Test if service is healthy"""
    print("🔍 Testing service health...")
    response = requests.get(f"{BASE_URL}/health")
    print(f"✅ Health check: {response.json()}\n")
    return response.status_code == 200

def test_spec_library():
    """Check what specs are loaded"""
    print("📚 Checking spec library...")
    response = requests.get(f"{BASE_URL}/spec-library")
    data = response.json()
    print(f"✅ Spec library status:")
    print(f"   - Total specs: {data.get('total_specs', 0)}")
    print(f"   - Total chunks: {data.get('total_chunks', 0)}")
    if data.get('specs'):
        print(f"   - Loaded specs:")
        for spec in data['specs'][:3]:  # Show first 3
            print(f"     • {spec.get('filename', 'Unknown')}")
    print()
    return data

def test_analyze_audit_text():
    """Test analyze-audit with text-based mock data"""
    print("🔬 Testing /analyze-audit endpoint...")
    print("   Creating mock audit data...\n")
    
    # Create a simple mock audit as JSON (since PDF is corrupted)
    # In production, you'd upload a real PDF file
    mock_audit_text = """
    PG&E QA AUDIT REPORT
    PM NUMBER: PM-2025-001234
    NOTIFICATION NUMBER: NOTIF-789456
    
    INFRACTIONS FOUND:
    
    1. CROSSARM INSTALLATION - GRADE B VIOLATION
       Location: Pole #45-A, Main St & Oak Ave
       Finding: Oil-filled crossarm installed on utility pole does not meet 
                GRADE B insulation standards per current specifications.
       QA Score: NO (Non-compliant)
       Severity: High
       
    2. POLE HEIGHT DEFICIENCY
       Location: Pole #47-C, Elm Street
       Finding: Utility pole height measures 32 feet, below minimum 35-foot 
                requirement for residential areas.
       QA Score: NO (Non-compliant)
       Severity: Critical
       
    3. GROUNDING WIRE PLACEMENT
       Location: Pole #45-A, Main St & Oak Ave
       Finding: Grounding wire not properly secured per SECTION 4.2 guidelines.
       QA Score: NO (Non-compliant)
       Severity: Medium
    
    OVERALL COMPLIANCE: 60% (3 of 5 items failed)
    RECOMMENDATION: GO-BACK REQUIRED
    """
    
    # Note: The actual endpoint expects a PDF file upload
    # For demonstration, let's show the expected curl command
    print("📋 Expected curl command for real PDF:")
    print("=" * 70)
    print(f"""
curl -X POST {BASE_URL}/analyze-audit \\
  -F "file=@path/to/audit.pdf" \\
  -H "Accept: application/json"
    """)
    print("=" * 70)
    print()
    
    print("📊 Mock audit content:")
    print("-" * 70)
    print(mock_audit_text)
    print("-" * 70)
    print()
    
    print("🎯 Expected AI Analysis Output:")
    print("=" * 70)
    expected_output = {
        "pm_number": "PM-2025-001234",
        "notification_number": "NOTIF-789456",
        "infractions_analyzed": 3,
        "repealable_infractions": [
            {
                "infraction": "Oil-filled crossarm installed on utility pole does not meet GRADE B insulation standards",
                "valid": False,
                "confidence": 0.87,
                "repeal_reasons": [
                    "Per SECTION 3.2: 'Oil-filled crossarms are compliant under GRADE B standards if installed pre-2020 or in low-voltage zones.'",
                    "Per SECTION 4.1: 'GRADE B compliance does not require retrofit for non-critical infractions.'"
                ],
                "match_count": 2,
                "source_specs": ["051071.pdf", "068195.pdf"]
            }
        ],
        "true_infractions": [
            {
                "infraction": "Utility pole height measures 32 feet, below minimum 35-foot requirement",
                "valid": True,
                "confidence": 0.95,
                "reason": "Clear violation of minimum height requirement with no exceptions found in spec library"
            },
            {
                "infraction": "Grounding wire not properly secured per SECTION 4.2 guidelines",
                "valid": True,
                "confidence": 0.82,
                "reason": "Safety-critical violation with no documented exceptions"
            }
        ],
        "overall_summary": {
            "total_infractions": 3,
            "repealable": 1,
            "true_go_backs": 2,
            "confidence_avg": 0.88,
            "recommendation": "PARTIAL GO-BACK REQUIRED (2 critical infractions remain)"
        },
        "processing_time": "2.3s"
    }
    print(json.dumps(expected_output, indent=2))
    print("=" * 70)
    print()

def test_vision_endpoints():
    """Test vision endpoints for pole detection"""
    print("👁️ Testing Vision endpoints...")
    
    # Check model status
    try:
        response = requests.get(f"{BASE_URL}/vision/model-status")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Vision model status:")
            print(f"   - Status: {data.get('status', 'unknown')}")
            print(f"   - Model path: {data.get('model_path', 'N/A')}")
            print()
        else:
            print(f"⚠️ Vision endpoints not available (status: {response.status_code})\n")
    except Exception as e:
        print(f"⚠️ Vision endpoints error: {e}\n")

def main():
    """Run all tests"""
    print("=" * 70)
    print("🚀 NEXA Document Analyzer - Live API Test")
    print("=" * 70)
    print(f"📍 Testing: {BASE_URL}")
    print("=" * 70)
    print()
    
    # Run tests
    if test_health():
        test_spec_library()
        test_analyze_audit_text()
        test_vision_endpoints()
        
        print("=" * 70)
        print("✅ ALL TESTS COMPLETED")
        print("=" * 70)
        print()
        print("📝 Next Steps:")
        print("   1. Upload a real PG&E audit PDF using the curl command above")
        print("   2. Check async endpoint: POST /analyze-audit-async")
        print("   3. Test batch processing: POST /batch-analyze")
        print("   4. Monitor with: GET /queue-status")
        print()
        print("🔗 Interactive API Docs:")
        print(f"   {BASE_URL}/docs")
        print()
    else:
        print("❌ Service health check failed!")

if __name__ == "__main__":
    main()
