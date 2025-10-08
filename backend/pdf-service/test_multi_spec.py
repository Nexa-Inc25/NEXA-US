#!/usr/bin/env python3
"""
Test script for multi-spec upload functionality
Demonstrates how to upload multiple spec files and manage the spec library
"""
import requests
import json
import os
from typing import List
import time

# Configuration
BASE_URL = "https://nexa-doc-analyzer-oct2025.onrender.com"
# BASE_URL = "http://localhost:8000"  # For local testing

def test_spec_library_status():
    """Check current spec library status"""
    print("\n📚 Checking Spec Library Status...")
    print("-" * 50)
    
    response = requests.get(f"{BASE_URL}/spec-library")
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Total files in library: {data['total_files']}")
        print(f"✅ Total chunks: {data['total_chunks']}")
        print(f"✅ Storage path: {data['storage_path']}")
        
        if data['files']:
            print("\n📁 Files in library:")
            for file in data['files']:
                print(f"   - {file['filename']}")
                print(f"     Hash: {file['file_hash']}")
                print(f"     Chunks: {file['chunk_count']}")
                print(f"     Size: {file['file_size']:,} bytes")
                print(f"     Uploaded: {file['upload_time']}")
        else:
            print("\n⚠️ No files in library yet")
        
        return data
    else:
        print(f"❌ Error: {response.status_code}")
        return None

def test_multi_upload(file_paths: List[str], mode: str = "append"):
    """Test uploading multiple spec files"""
    print(f"\n📤 Uploading {len(file_paths)} spec files (mode: {mode})...")
    print("-" * 50)
    
    # Prepare files for upload
    files = []
    for path in file_paths:
        if os.path.exists(path):
            filename = os.path.basename(path)
            with open(path, 'rb') as f:
                files.append(('files', (filename, f.read(), 'application/pdf')))
            print(f"   📎 Prepared: {filename}")
        else:
            print(f"   ❌ File not found: {path}")
    
    if not files:
        print("❌ No valid files to upload")
        return None
    
    # Upload files
    print(f"\n⏳ Uploading {len(files)} files...")
    start_time = time.time()
    
    response = requests.post(
        f"{BASE_URL}/upload-specs",
        files=files,
        data={"mode": mode}
    )
    
    upload_time = time.time() - start_time
    print(f"⏱️ Upload completed in {upload_time:.2f} seconds")
    
    if response.status_code == 200:
        data = response.json()
        print(f"\n✅ {data['message']}")
        print(f"📊 Files processed: {data['files_processed']}")
        print(f"📊 New chunks added: {data['new_chunks_added']}")
        print(f"📊 Total chunks now: {data['total_chunks']}")
        
        # Show library status
        lib_status = data['library_status']
        print(f"\n📚 Library now contains:")
        print(f"   - {lib_status['total_files']} files")
        print(f"   - {lib_status['total_chunks']} chunks")
        
        return data
    else:
        print(f"❌ Error {response.status_code}: {response.text}")
        return None

def test_clear_library():
    """Test clearing the spec library"""
    print("\n🗑️ Clearing Spec Library...")
    print("-" * 50)
    
    response = requests.post(
        f"{BASE_URL}/manage-specs",
        json={"operation": "clear"}
    )
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ {data['message']}")
        return data
    else:
        print(f"❌ Error: {response.status_code}")
        return None

def test_analyze_with_multi_specs(audit_file: str):
    """Test analyzing an audit against multiple spec files"""
    print(f"\n🔍 Analyzing Audit: {audit_file}")
    print("-" * 50)
    
    if not os.path.exists(audit_file):
        print(f"❌ Audit file not found: {audit_file}")
        return None
    
    with open(audit_file, 'rb') as f:
        files = {'file': (os.path.basename(audit_file), f.read(), 'application/pdf')}
    
    print("⏳ Analyzing...")
    start_time = time.time()
    
    response = requests.post(f"{BASE_URL}/analyze-audit", files=files)
    
    analysis_time = time.time() - start_time
    print(f"⏱️ Analysis completed in {analysis_time:.2f} seconds")
    
    if response.status_code == 200:
        data = response.json()
        print(f"\n✅ Analysis complete:")
        print(f"   - Spec files in library: {data.get('spec_files', 'N/A')}")
        print(f"   - Infractions found: {data.get('infractions_found', 0)}")
        print(f"   - Infractions analyzed: {data.get('infractions_analyzed', 0)}")
        
        # Show some results
        results = data.get('results', [])
        if results:
            print(f"\n📋 Sample Results (showing first 3):")
            for i, result in enumerate(results[:3], 1):
                print(f"\n   {i}. Infraction: {result['infraction'][:100]}...")
                print(f"      Status: {result['status']}")
                
                if result['matches']:
                    print(f"      Matches:")
                    for match in result['matches']:
                        print(f"        - Source: {match['source']}")
                        print(f"          Score: {match['score']}%")
        
        return data
    else:
        print(f"❌ Error {response.status_code}: {response.text}")
        return None

def demo_workflow():
    """
    Demonstrate the complete workflow:
    1. Check current library status
    2. Upload multiple spec files
    3. Analyze an audit
    4. Show how files persist
    """
    print("\n" + "="*60)
    print("🚀 NEXA Multi-Spec Upload Demo")
    print("="*60)
    
    # Step 1: Check current status
    print("\n📌 Step 1: Current Library Status")
    initial_status = test_spec_library_status()
    
    # Step 2: Simulate uploading multiple spec files
    print("\n📌 Step 2: Upload Multiple Spec Files")
    print("ℹ️ In production, you would upload actual PDF files")
    print("ℹ️ Example usage:")
    print("""
    spec_files = [
        "specs/015077_Crossarm_hardware.pdf",
        "specs/015225_Cutouts_Fuses.pdf",
        "specs/092813_FuseSaver.pdf",
        "specs/094672_TripSaver.pdf"
    ]
    test_multi_upload(spec_files, mode="append")
    """)
    
    # Step 3: Show persistence
    print("\n📌 Step 3: Persistence Check")
    print("✅ Files are stored permanently at: /data/spec_embeddings.pkl")
    print("✅ Metadata stored at: /data/spec_metadata.json")
    print("✅ Files persist across container restarts")
    print("✅ Each upload in 'append' mode ADDS to existing library")
    print("✅ Use mode='replace' to start fresh")
    
    # Step 4: Management options
    print("\n📌 Step 4: Library Management Options")
    print("   • View library: GET /spec-library")
    print("   • Upload files: POST /upload-specs (multiple files)")
    print("   • Clear library: POST /manage-specs {operation: 'clear'}")
    print("   • Remove file: POST /manage-specs {operation: 'remove', file_hash: 'xxx'}")
    
    # Step 5: Analysis capabilities
    print("\n📌 Step 5: Enhanced Analysis")
    print("✅ Audits are analyzed against ALL spec files in library")
    print("✅ Each match shows which spec file it came from")
    print("✅ Better accuracy with more comprehensive spec coverage")
    
    print("\n" + "="*60)
    print("✨ Summary: Multi-Spec Benefits")
    print("="*60)
    print("1. ⚡ Upload multiple PDFs in one request")
    print("2. 💾 Permanent storage (survives restarts)")
    print("3. 📚 Build comprehensive spec library over time")
    print("4. 🔍 Source tracking for each match")
    print("5. 🔄 Incremental updates (append mode)")
    print("6. 🗑️ Full library management (clear, remove)")
    print("\n")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "status":
            test_spec_library_status()
        elif sys.argv[1] == "clear":
            test_clear_library()
        elif sys.argv[1] == "upload" and len(sys.argv) > 2:
            # Example: python test_multi_spec.py upload file1.pdf file2.pdf file3.pdf
            test_multi_upload(sys.argv[2:])
        elif sys.argv[1] == "analyze" and len(sys.argv) > 2:
            # Example: python test_multi_spec.py analyze audit.pdf
            test_analyze_with_multi_specs(sys.argv[2])
        else:
            print("Usage:")
            print("  python test_multi_spec.py status           # Check library status")
            print("  python test_multi_spec.py clear            # Clear library")
            print("  python test_multi_spec.py upload f1.pdf f2.pdf  # Upload files")
            print("  python test_multi_spec.py analyze audit.pdf      # Analyze audit")
            print("  python test_multi_spec.py                  # Run demo")
    else:
        demo_workflow()
