#!/usr/bin/env python3
"""
Test script to verify the spec-library endpoint fix
"""
import requests
import time

def test_spec_library(base_url):
    """Test the /spec-library endpoint"""
    print(f"\n🔍 Testing /spec-library endpoint at {base_url}")
    print("-" * 50)
    
    try:
        # Test the endpoint
        response = requests.get(f"{base_url}/spec-library", timeout=10)
        
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("✅ SUCCESS! Endpoint is working")
            print(f"\nLibrary Status:")
            print(f"  • Total files: {data.get('total_files', 0)}")
            print(f"  • Total chunks: {data.get('total_chunks', 0)}")
            print(f"  • Storage path: {data.get('storage_path', 'N/A')}")
            print(f"  • Last updated: {data.get('last_updated', 'Never')}")
            
            if data.get('files'):
                print(f"\n📄 Files in library:")
                for file in data['files'][:5]:  # Show first 5 files
                    print(f"    - {file.get('filename', 'Unknown')}")
                    print(f"      Hash: {file.get('file_hash', 'N/A')}")
                    print(f"      Chunks: {file.get('chunks', 0)}")
        else:
            print(f"❌ ERROR: {response.status_code}")
            print(f"Response: {response.text}")
            
    except requests.exceptions.Timeout:
        print("❌ Request timed out")
    except requests.exceptions.ConnectionError:
        print("❌ Could not connect to server")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")

if __name__ == "__main__":
    # Local test
    print("\n🏠 Testing Local Instance...")
    test_spec_library("http://localhost:8000")
    
    # Production test (update with your actual Render URL)
    print("\n🌐 Testing Production Instance...")
    # Replace with your actual Render deployment URL
    prod_url = "https://nexa-doc-analyzer-oct2025.onrender.com"
    
    print(f"Waiting for deployment to complete...")
    print("(This may take 5-10 minutes after pushing to GitHub)")
    
    # Wait a bit for deployment
    time.sleep(5)
    
    test_spec_library(prod_url)
    
    print("\n✨ Test complete!")
