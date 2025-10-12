"""
Test script for AI Document Analyzer
Run this to verify everything is working
"""
import os
from utils import (
    GrokLLM,
    extract_infractions,
    validate_environment
)

def test_environment():
    """Test environment setup"""
    print("Testing Environment Setup...")
    checks = validate_environment()
    
    for key, value in checks.items():
        status = "PASS" if value else "FAIL"
        print(f"[{status}] {key}: {value}")
    
    return all(checks.values())

def test_grok_api():
    """Test xAI/Grok API connection"""
    print("\nTesting xAI API...")
    try:
        llm = GrokLLM()
        response = llm("Hello, this is a test. Respond with 'API Working'")
        print(f"[PASS] API Response: {response[:100]}")
        return True
    except Exception as e:
        print(f"[FAIL] API Error: {e}")
        return False

def test_infraction_extraction():
    """Test infraction extraction patterns"""
    print("\nTesting Infraction Extraction...")
    
    test_text = """
    Audit Report - Transformer Installation
    
    Go-back: Pad not level per specification 045292
    Infraction: Missing grounding wire at pole 123
    Violation: Clearance less than required 10 feet
    Non-compliance: Incorrect fusing installed
    Defect: Oil leak detected at transformer base
    Installation error: Guy wire anchor not at correct angle
    Safety violation: No warning signs posted
    Minor issue: Paint chipped on cabinet door
    """
    
    infractions = extract_infractions(test_text)
    
    print(f"Found {len(infractions)} infractions:")
    for i, inf in enumerate(infractions, 1):
        print(f"{i}. [{inf['severity']}] {inf['type']}: {inf['description'][:50]}...")
    
    return len(infractions) >= 5

def test_sample_pdfs():
    """Check if sample PDFs are available"""
    print("\nChecking for Sample PDFs...")
    
    sample_specs = [
        "045786 open wye to zig-zag wye transformation equipment.pdf",
        "045292 concrete pad extension for pad-mounted equipment.pdf",
        "046066 autotransformer wiring diagrams.pdf"
    ]
    
    found = 0
    for spec in sample_specs:
        if os.path.exists(f"data/{spec}"):
            print(f"[FOUND] {spec}")
            found += 1
        else:
            print(f"[MISSING] {spec} (upload via UI)")
    
    return found > 0

def main():
    """Run all tests"""
    print("=" * 50)
    print("AI Document Analyzer - System Test")
    print("=" * 50)
    
    results = {
        "Environment": test_environment(),
        "Infraction Extraction": test_infraction_extraction(),
        "xAI API": test_grok_api() if os.getenv("XAI_API_KEY") else False,
        "Sample PDFs": test_sample_pdfs()
    }
    
    print("\n" + "=" * 50)
    print("Test Summary:")
    print("=" * 50)
    
    for test, passed in results.items():
        status = "PASSED" if passed else "FAILED"
        print(f"{test}: {status}")
    
    all_passed = all(results.values())
    
    if all_passed:
        print("\nAll tests passed! System ready for use.")
    else:
        print("\nSome tests failed. Check configuration:")
        if not results["Environment"]:
            print("- Set XAI_API_KEY in .env file")
        if not results["xAI API"]:
            print("- Verify xAI API key is valid")
        if not results["Sample PDFs"]:
            print("- Upload spec PDFs via the UI")
    
    print("\nAccess the app at: http://localhost:8506")
    print("Documentation: DEPLOY_TO_RENDER.md")

if __name__ == "__main__":
    main()
