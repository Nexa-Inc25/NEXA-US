#!/usr/bin/env python3
"""
Script to clear the spec library on the deployed service
"""
import requests
import json

def clear_library(base_url):
    """Clear the spec library"""
    print(f"\n🧹 Clearing spec library at {base_url}")
    print("-" * 50)
    
    try:
        # Clear the library
        response = requests.post(
            f"{base_url}/manage-specs",
            json={"operation": "clear"},
            timeout=10
        )
        
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("✅ SUCCESS! Library cleared")
            print(f"Message: {data.get('message', 'Library cleared')}")
        else:
            print(f"❌ ERROR: {response.status_code}")
            print(f"Response: {response.text}")
            
    except Exception as e:
        print(f"❌ Error: {e}")

def check_library(base_url):
    """Check library status"""
    print(f"\n📚 Checking library status...")
    
    try:
        response = requests.get(f"{base_url}/spec-library", timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Library Status:")
            print(f"  • Total files: {data.get('total_files', 0)}")
            print(f"  • Total chunks: {data.get('total_chunks', 0)}")
            print(f"  • Storage path: {data.get('storage_path', 'N/A')}")
        else:
            print(f"❌ Error checking library: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    # Production URL
    prod_url = "https://nexa-doc-analyzer-oct2025.onrender.com"
    
    # Check current status
    print("📊 Current Status:")
    check_library(prod_url)
    
    # Clear the library
    print("\n🚀 Clearing library...")
    clear_library(prod_url)
    
    # Check status after clear
    print("\n📊 Status After Clear:")
    check_library(prod_url)
    
    print("\n✨ You can now re-upload your spec files!")
