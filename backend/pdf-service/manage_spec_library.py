#!/usr/bin/env python3
"""
Spec Library Management Tool for NEXA Document Analyzer
Provides options to view, clear, or selectively manage spec files
"""

import requests
import json
from typing import List, Dict, Optional
import sys
from datetime import datetime

# Configuration
API_URL = "https://nexa-doc-analyzer-oct2025.onrender.com"
# API_URL = "http://localhost:8000"  # Uncomment for local testing

def get_library_status() -> Dict:
    """Get current spec library status"""
    try:
        response = requests.get(f"{API_URL}/spec-library")
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Error fetching library status: {e}")
        return {}

def clear_library() -> bool:
    """Clear entire spec library"""
    try:
        # Using the manage-specs endpoint with clear operation
        response = requests.post(
            f"{API_URL}/manage-specs",
            json={"operation": "clear"}
        )
        response.raise_for_status()
        print("✅ Library cleared successfully")
        return True
    except Exception as e:
        print(f"❌ Error clearing library: {e}")
        return False

def remove_file(filename: str) -> bool:
    """Remove a specific file from the library"""
    try:
        response = requests.post(
            f"{API_URL}/manage-specs",
            json={
                "operation": "remove",
                "filename": filename
            }
        )
        response.raise_for_status()
        print(f"✅ Removed: {filename}")
        return True
    except Exception as e:
        print(f"❌ Error removing {filename}: {e}")
        return False

def display_library_info(library: Dict):
    """Display formatted library information"""
    print("\n" + "="*60)
    print("📚 NEXA SPEC LIBRARY STATUS")
    print("="*60)
    
    total_files = library.get('total_files', 0)
    total_chunks = library.get('total_chunks', 0)
    last_updated = library.get('last_updated')
    
    print(f"\n📊 Summary:")
    print(f"   Total Files: {total_files}")
    print(f"   Total Chunks: {total_chunks}")
    if last_updated:
        try:
            dt = datetime.fromisoformat(last_updated.replace('Z', '+00:00'))
            print(f"   Last Updated: {dt.strftime('%Y-%m-%d %H:%M:%S UTC')}")
        except:
            print(f"   Last Updated: {last_updated}")
    
    files = library.get('files', [])
    if files:
        print(f"\n📁 Files in Library ({len(files)}):")
        print("-" * 60)
        
        # Sort files by upload time (newest first)
        sorted_files = sorted(files, key=lambda x: x.get('upload_time', ''), reverse=True)
        
        for i, file_info in enumerate(sorted_files[:20], 1):  # Show first 20
            filename = file_info.get('filename', 'Unknown')
            chunks = file_info.get('chunk_count', 0)
            size = file_info.get('file_size', 0)
            
            # Format file size
            if size > 1024*1024:
                size_str = f"{size/(1024*1024):.1f}MB"
            elif size > 1024:
                size_str = f"{size/1024:.1f}KB"
            else:
                size_str = f"{size}B"
            
            print(f"   {i:3d}. {filename[:50]:50s} | {chunks:3d} chunks | {size_str:>8s}")
        
        if len(files) > 20:
            print(f"\n   ... and {len(files) - 20} more files")

def force_reupload_file(filepath: str) -> bool:
    """Force re-upload a file by removing it first then uploading"""
    import os
    
    if not os.path.exists(filepath):
        print(f"❌ File not found: {filepath}")
        return False
    
    filename = os.path.basename(filepath)
    
    # First remove the file if it exists
    print(f"Removing existing: {filename}")
    remove_file(filename)
    
    # Then upload the new version
    print(f"Uploading: {filename}")
    try:
        with open(filepath, 'rb') as f:
            files = {'file': (filename, f, 'application/pdf')}
            response = requests.post(f"{API_URL}/learn-spec/", files=files)
            response.raise_for_status()
            result = response.json()
            print(f"✅ Uploaded successfully: {result.get('chunks_processed', 0)} chunks")
            return True
    except Exception as e:
        print(f"❌ Error uploading: {e}")
        return False

def main():
    """Main menu for library management"""
    while True:
        print("\n" + "="*60)
        print("🔧 NEXA SPEC LIBRARY MANAGER")
        print("="*60)
        print("\n1. View library status")
        print("2. Clear entire library")
        print("3. Remove specific file")
        print("4. Force re-upload file")
        print("5. Export library list to JSON")
        print("6. Exit")
        
        choice = input("\nSelect option (1-6): ").strip()
        
        if choice == '1':
            library = get_library_status()
            if library:
                display_library_info(library)
            else:
                print("Failed to fetch library status")
        
        elif choice == '2':
            confirm = input("\n⚠️  This will DELETE all spec files. Continue? (yes/no): ").strip().lower()
            if confirm == 'yes':
                clear_library()
                print("\nLibrary has been cleared. You can now re-upload specs.")
            else:
                print("Cancelled")
        
        elif choice == '3':
            library = get_library_status()
            files = library.get('files', [])
            if not files:
                print("No files in library")
                continue
            
            print("\nFiles in library:")
            for i, f in enumerate(files[:30], 1):
                print(f"{i:3d}. {f.get('filename', 'Unknown')}")
            
            if len(files) > 30:
                print(f"... and {len(files)-30} more")
            
            file_num = input("\nEnter file number to remove (or 'cancel'): ").strip()
            if file_num.isdigit() and 1 <= int(file_num) <= len(files):
                file_to_remove = files[int(file_num)-1].get('filename')
                confirm = input(f"Remove '{file_to_remove}'? (yes/no): ").strip().lower()
                if confirm == 'yes':
                    remove_file(file_to_remove)
        
        elif choice == '4':
            filepath = input("\nEnter full path to PDF file: ").strip()
            if filepath:
                force_reupload_file(filepath)
        
        elif choice == '5':
            library = get_library_status()
            if library:
                filename = f"spec_library_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                with open(filename, 'w') as f:
                    json.dump(library, f, indent=2)
                print(f"✅ Library exported to {filename}")
        
        elif choice == '6':
            print("\nGoodbye!")
            break
        
        else:
            print("Invalid option. Please try again.")

if __name__ == "__main__":
    main()
