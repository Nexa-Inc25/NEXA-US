#!/usr/bin/env python3
"""
Test persistence of spec entities after server restart
"""
import requests
import time
import subprocess
import sys

def test_persistence():
    """Test that spec entities persist after restart"""
    
    print("=" * 60)
    print("Testing Persistence of Electrical Spec Analyzer")
    print("=" * 60)
    
    # Check initial status
    print("\n1. Checking current status...")
    try:
        response = requests.get("http://localhost:8002/status")
        status = response.json()
        print(f"   ✓ Spec loaded: {status['spec_loaded']}")
        print(f"   ✓ Entities count: {status['total_spec_entities']}")
        print(f"   ✓ Spec PDF exists: {status['spec_pdf_exists']}")
        print(f"   ✓ Pickle exists: {status['entities_pickle_exists']}")
    except:
        print("   ✗ Server not running on port 8002")
        return
    
    print("\n2. Server is running. Please:")
    print("   - Press Ctrl+C in the server terminal to stop it")
    print("   - Then restart it with: python app_electrical.py")
    print("   - Check the console output for '✅ Loaded persisted spec entities'")
    print("\n3. Once restarted, press Enter here to continue testing...")
    input()
    
    # Wait for server to be ready
    print("\n4. Checking persistence after restart...")
    max_attempts = 10
    for i in range(max_attempts):
        try:
            response = requests.get("http://localhost:8002/status")
            status = response.json()
            print(f"\n   ✅ Server is back online!")
            print(f"   ✓ Spec still loaded: {status['spec_loaded']}")
            print(f"   ✓ Entities preserved: {status['total_spec_entities']}")
            print(f"   ✓ Spec PDF exists: {status['spec_pdf_exists']}")
            print(f"   ✓ Pickle exists: {status['entities_pickle_exists']}")
            
            if status['spec_loaded']:
                print("\n   🎉 SUCCESS! Spec entities persisted across restart!")
            else:
                print("\n   ⚠️  Warning: Spec not loaded after restart")
            break
        except:
            if i < max_attempts - 1:
                print(f"   Waiting for server... ({i+1}/{max_attempts})")
                time.sleep(2)
            else:
                print("   ✗ Server did not come back online")
                return
    
    print("\n5. Testing audit analysis with persisted spec...")
    # Upload and analyze audit
    with open("test_audit.pdf", "rb") as f:
        files = {"file": ("test_audit.pdf", f, "application/pdf")}
        response = requests.post("http://localhost:8002/upload_audit", files=files)
        
    if response.status_code == 200:
        result = response.json()
        print(f"   ✓ Audit analyzed successfully!")
        print(f"   ✓ Found {result.get('infractions_count', 0)} infractions")
        print(f"   ✓ Spec was loaded: {result.get('spec_loaded', False)}")
        
        if 'analysis' in result and result['analysis']:
            print("\n   Sample analysis results:")
            for i, infraction in enumerate(result['analysis'][:2], 1):
                print(f"\n   Infraction {i}:")
                print(f"     - Repealable: {infraction.get('repealable', False)}")
                print(f"     - Confidence: {infraction.get('confidence', 0)}%")
                if 'reasons' in infraction and infraction['reasons']:
                    print(f"     - Reason: {infraction['reasons'][0]}")
    else:
        print(f"   ✗ Error analyzing audit: {response.status_code}")
    
    print("\n" + "=" * 60)
    print("Persistence Test Complete!")
    print("=" * 60)

if __name__ == "__main__":
    test_persistence()
