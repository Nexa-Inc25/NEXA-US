#!/usr/bin/env python3
"""
Batch Upload Script for 50 Spec PDFs
Handles large spec book split into multiple sections
"""
import os
import requests
import time
import glob
from pathlib import Path
import json
from typing import List, Dict
import sys

# Configuration
API_URL = "https://nexa-doc-analyzer-oct2025.onrender.com"
# API_URL = "http://localhost:8000"  # For local testing

# Batch size - upload in groups to avoid timeouts
BATCH_SIZE = 10  # Upload 10 files at a time

def format_size(bytes):
    """Format bytes to human readable"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if bytes < 1024.0:
            return f"{bytes:.2f} {unit}"
        bytes /= 1024.0
    return f"{bytes:.2f} TB"

def get_spec_files(directory: str) -> List[Path]:
    """Find all PDF files in directory"""
    patterns = [
        '*.pdf', '*.PDF',
        '**/*.pdf', '**/*.PDF'  # Include subdirectories
    ]
    
    files = []
    for pattern in patterns:
        files.extend(Path(directory).glob(pattern))
    
    # Sort files for consistent ordering
    files = sorted(set(files))
    
    print(f"\n📁 Found {len(files)} PDF files in {directory}")
    
    # Show summary
    total_size = sum(f.stat().st_size for f in files)
    print(f"📊 Total size: {format_size(total_size)}")
    
    return files

def check_library_status() -> Dict:
    """Check current library status"""
    try:
        response = requests.get(f"{API_URL}/spec-library", timeout=10)
        if response.status_code == 200:
            return response.json()
    except Exception as e:
        print(f"⚠️ Could not check library status: {e}")
    return {}

def upload_batch(files: List[Path], batch_num: int, total_batches: int, mode: str = "append") -> bool:
    """Upload a batch of files"""
    print(f"\n📤 Uploading batch {batch_num}/{total_batches} ({len(files)} files)")
    print("-" * 50)
    
    # Prepare multipart upload
    file_handles = []
    files_data = []
    
    try:
        # Open all files
        for file_path in files:
            print(f"   📎 {file_path.name} ({format_size(file_path.stat().st_size)})")
            f = open(file_path, 'rb')
            file_handles.append(f)
            files_data.append(('files', (file_path.name, f, 'application/pdf')))
        
        # Upload with progress tracking
        print(f"\n⏳ Uploading batch {batch_num}...")
        start_time = time.time()
        
        response = requests.post(
            f"{API_URL}/upload-specs",
            files=files_data,
            data={"mode": mode},
            timeout=300  # 5 minute timeout for large uploads
        )
        
        upload_time = time.time() - start_time
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Batch {batch_num} complete in {upload_time:.1f}s")
            print(f"   • Files processed: {data['files_processed']}")
            print(f"   • New chunks added: {data['new_chunks_added']}")
            print(f"   • Total chunks now: {data['total_chunks']}")
            return True
        else:
            print(f"❌ Batch {batch_num} failed: {response.status_code}")
            print(f"   Error: {response.text[:200]}")
            return False
            
    except requests.exceptions.Timeout:
        print(f"⏱️ Batch {batch_num} timed out - files may be too large")
        return False
    except Exception as e:
        print(f"❌ Batch {batch_num} error: {e}")
        return False
    finally:
        # Close all file handles
        for f in file_handles:
            f.close()

def batch_upload_specs(directory: str, mode: str = "append"):
    """Upload all spec PDFs in batches"""
    print("\n" + "="*60)
    print("🚀 NEXA BATCH SPEC UPLOAD - 50 SECTIONS")
    print("="*60)
    
    # Check initial status
    print("\n📊 Checking current library status...")
    initial_status = check_library_status()
    if initial_status:
        print(f"   • Current files: {initial_status.get('total_files', 0)}")
        print(f"   • Current chunks: {initial_status.get('total_chunks', 0)}")
        
        if mode == "append" and initial_status.get('total_files', 0) > 0:
            response = input("\n⚠️ Library already contains files. Continue with append? (y/n): ")
            if response.lower() != 'y':
                print("Upload cancelled.")
                return
    
    # Find all PDF files
    files = get_spec_files(directory)
    
    if not files:
        print("❌ No PDF files found!")
        return
    
    # Confirm upload
    print(f"\n📋 Ready to upload {len(files)} files in {mode} mode")
    print(f"📦 Will upload in batches of {BATCH_SIZE} files")
    
    # Show first few files as preview
    print("\n📄 First 5 files:")
    for f in files[:5]:
        print(f"   • {f.name}")
    if len(files) > 5:
        print(f"   ... and {len(files) - 5} more")
    
    response = input("\n🚀 Start upload? (y/n): ")
    if response.lower() != 'y':
        print("Upload cancelled.")
        return
    
    # Upload in batches
    total_batches = (len(files) + BATCH_SIZE - 1) // BATCH_SIZE
    successful_batches = 0
    failed_files = []
    
    print(f"\n📦 Starting upload of {len(files)} files in {total_batches} batches")
    print("="*60)
    
    start_time = time.time()
    
    for i in range(0, len(files), BATCH_SIZE):
        batch = files[i:i + BATCH_SIZE]
        batch_num = (i // BATCH_SIZE) + 1
        
        # Use "append" for all batches after the first if mode was "replace"
        batch_mode = mode if batch_num == 1 else "append"
        
        success = upload_batch(batch, batch_num, total_batches, batch_mode)
        
        if success:
            successful_batches += 1
        else:
            failed_files.extend(batch)
        
        # Small delay between batches to avoid overwhelming server
        if batch_num < total_batches:
            print(f"\n⏸️ Waiting 2 seconds before next batch...")
            time.sleep(2)
    
    # Final summary
    total_time = time.time() - start_time
    
    print("\n" + "="*60)
    print("📊 UPLOAD SUMMARY")
    print("="*60)
    print(f"✅ Successful batches: {successful_batches}/{total_batches}")
    print(f"📁 Files uploaded: {len(files) - len(failed_files)}/{len(files)}")
    print(f"⏱️ Total time: {total_time:.1f} seconds")
    
    if failed_files:
        print(f"\n⚠️ Failed files ({len(failed_files)}):")
        for f in failed_files[:10]:
            print(f"   • {f.name}")
        if len(failed_files) > 10:
            print(f"   ... and {len(failed_files) - 10} more")
    
    # Check final status
    print("\n📊 Checking final library status...")
    final_status = check_library_status()
    if final_status:
        print(f"✅ Final library contains:")
        print(f"   • Total files: {final_status.get('total_files', 0)}")
        print(f"   • Total chunks: {final_status.get('total_chunks', 0)}")
        
        # Show uploaded files
        if final_status.get('files'):
            print(f"\n📚 Files in library:")
            for file in final_status['files'][-5:]:  # Show last 5
                print(f"   • {file['filename']} ({file['chunk_count']} chunks)")
            if len(final_status['files']) > 5:
                print(f"   ... and {len(final_status['files']) - 5} more")
    
    print("\n✅ Batch upload complete!")
    print("🎯 Your 50-section spec book is now ready for use!")

def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Batch upload 50 spec PDFs to NEXA')
    parser.add_argument('directory', nargs='?', default='.', 
                       help='Directory containing PDF files (default: current directory)')
    parser.add_argument('--mode', choices=['append', 'replace'], default='append',
                       help='Upload mode: append to existing or replace all (default: append)')
    parser.add_argument('--batch-size', type=int, default=BATCH_SIZE,
                       help=f'Number of files per batch (default: {BATCH_SIZE})')
    parser.add_argument('--local', action='store_true',
                       help='Use local API instead of Render')
    
    args = parser.parse_args()
    
    # Update settings
    global API_URL, BATCH_SIZE
    if args.local:
        API_URL = "http://localhost:8000"
    BATCH_SIZE = args.batch_size
    
    # Check directory exists
    if not os.path.exists(args.directory):
        print(f"❌ Directory not found: {args.directory}")
        sys.exit(1)
    
    # Run batch upload
    batch_upload_specs(args.directory, args.mode)

if __name__ == "__main__":
    main()
