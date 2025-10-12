#!/usr/bin/env python3
"""
Test script for Mega Bundle Analysis feature
Creates sample data and tests the complete workflow
"""

import os
import json
import zipfile
import requests
import pandas as pd
from pathlib import Path
import time
import random

# Configuration
API_BASE_URL = "http://localhost:8001"

def create_test_bundle(num_jobs=100):
    """Create a test ZIP file with sample job PDFs"""
    
    print(f"📦 Creating test bundle with {num_jobs} jobs...")
    
    # Job tags and their distribution
    job_tags = {
        "07D": 0.4,  # 40% pole replacements
        "KAA": 0.25,  # 25% crossarms
        "2AA": 0.15,  # 15% anchors
        "TRX": 0.10,  # 10% transformers
        "UG1": 0.10   # 10% underground
    }
    
    # Create temporary directory for PDFs
    temp_dir = Path("temp_jobs")
    temp_dir.mkdir(exist_ok=True)
    
    # Generate sample PDFs
    jobs_created = []
    for i in range(num_jobs):
        # Select job tag based on distribution
        rand = random.random()
        cumulative = 0
        selected_tag = "07D"
        for tag, prob in job_tags.items():
            cumulative += prob
            if rand <= cumulative:
                selected_tag = tag
                break
        
        # Generate coordinates (Sacramento area)
        lat = 38.5816 + random.uniform(-0.5, 0.5)
        lon = -121.4944 + random.uniform(-0.5, 0.5)
        
        # Create PDF content (text file for demo)
        pdf_content = f"""JOB PACKAGE
PM NUMBER: PM-2025-{i:04d}
NOTIFICATION NUMBER: N-2025-{i:04d}
JOB TYPE: {selected_tag}
LOCATION: Sacramento, CA
COORDINATES: {lat:.6f}, {lon:.6f}

SCOPE OF WORK:
- {selected_tag} Installation/Replacement
- Material Requirements:
  * Poles: {random.randint(1, 3)}
  * Crossarms: {random.randint(0, 2)}
  * Anchors: {random.randint(0, 4)}

SPECIAL REQUIREMENTS:
{"- Bucket truck required" if random.random() > 0.5 else ""}
{"- Crane required" if random.random() > 0.8 else ""}
{"- Traffic control needed" if random.random() > 0.6 else ""}

ESTIMATED DURATION: {random.randint(4, 12)} hours
CREW SIZE: {random.randint(3, 6)} workers
"""
        
        # Save as PDF (text file)
        pdf_path = temp_dir / f"job_{i:04d}.pdf"
        with open(pdf_path, 'w') as f:
            f.write(pdf_content)
        
        jobs_created.append({
            "id": f"PM-2025-{i:04d}",
            "tag": selected_tag,
            "coordinates": (lat, lon)
        })
    
    # Create ZIP file
    zip_path = "test_bundle.zip"
    with zipfile.ZipFile(zip_path, 'w') as zf:
        for pdf_file in temp_dir.glob("*.pdf"):
            zf.write(pdf_file, pdf_file.name)
    
    # Cleanup temp directory
    import shutil
    shutil.rmtree(temp_dir)
    
    print(f"✅ Created {zip_path} ({os.path.getsize(zip_path) / 1024:.1f} KB)")
    
    return zip_path, jobs_created

def create_test_bid_sheet():
    """Create a sample bid sheet CSV"""
    
    print("💰 Creating test bid sheet...")
    
    bid_data = {
        "Tag": ["07D", "KAA", "2AA", "TRX", "UG1"],
        "Description": [
            "Pole Replacement - Distribution",
            "Crossarm Installation", 
            "Anchor Installation",
            "Transformer Installation",
            "Underground Primary"
        ],
        "Unit_Price": [5000, 2000, 1000, 8000, 6000],
        "Unit": ["EA", "EA", "EA", "EA", "LF"]
    }
    
    df = pd.DataFrame(bid_data)
    bid_path = "test_bid_sheet.csv"
    df.to_csv(bid_path, index=False)
    
    print(f"✅ Created {bid_path}")
    
    return bid_path

def create_test_contract():
    """Create a sample contract PDF"""
    
    print("📄 Creating test contract...")
    
    contract_content = """CONTRACT AGREEMENT
PG&E UTILITY SERVICES

RATE SCHEDULE:
1. Labor Rates:
   - Journeyman Lineman: $85/hour
   - Apprentice: $65/hour
   - Groundman: $45/hour

2. Equipment Rates:
   - Bucket Truck: $150/hour
   - Crane: $300/hour
   - Digger Derrick: $200/hour

3. Unit Prices by Job Type:
   - 07D (Pole Replacement): $5,000 per unit
   - KAA (Crossarm): $2,000 per unit
   - 2AA (Anchor): $1,000 per unit
   - TRX (Transformer): $8,000 per unit
   - UG1 (Underground): $6,000 per linear foot

4. Overhead and Profit:
   - Overhead: 15%
   - Target Profit Margin: 20%

5. Special Conditions:
   - Weekend work: 1.5x labor rates
   - Holiday work: 2.0x labor rates
   - Emergency response: +25% premium
"""
    
    contract_path = "test_contract.pdf"
    with open(contract_path, 'w') as f:
        f.write(contract_content)
    
    print(f"✅ Created {contract_path}")
    
    return contract_path

def test_upload_bundle(mode="post-win", num_jobs=100):
    """Test bundle upload via API"""
    
    print(f"\n🚀 Testing mega bundle upload in {mode} mode...")
    
    # Create test files
    bundle_path, jobs = create_test_bundle(num_jobs)
    bid_path = create_test_bid_sheet()
    contract_path = create_test_contract() if mode == "post-win" else None
    
    # Prepare upload
    files = {
        'job_zip': ('test_bundle.zip', open(bundle_path, 'rb'), 'application/zip'),
        'bid_sheet': ('test_bid_sheet.csv', open(bid_path, 'rb'), 'text/csv')
    }
    
    if contract_path:
        files['contract'] = ('test_contract.pdf', open(contract_path, 'rb'), 'application/pdf')
    
    params = {
        'mode': mode,
        'profit_margin': 0.20,
        'max_daily_hours': 12,
        'prioritize': 'profit'
    }
    
    try:
        # Upload bundle
        print("📤 Uploading bundle to API...")
        response = requests.post(
            f"{API_BASE_URL}/mega-bundle/upload",
            files=files,
            params=params,
            timeout=60
        )
        
        if response.status_code == 200:
            result = response.json()
            bundle_id = result['bundle_id']
            print(f"✅ Bundle uploaded successfully!")
            print(f"   Bundle ID: {bundle_id}")
            print(f"   Status: {result['status']}")
            
            # Poll for completion
            print("\n⏳ Processing bundle...")
            return poll_for_completion(bundle_id)
        else:
            print(f"❌ Upload failed: {response.status_code}")
            print(response.text)
            return None
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return None
    finally:
        # Cleanup
        for path in [bundle_path, bid_path, contract_path]:
            if path and os.path.exists(path):
                os.remove(path)

def poll_for_completion(bundle_id, max_polls=60):
    """Poll for bundle processing completion"""
    
    for i in range(max_polls):
        try:
            response = requests.get(f"{API_BASE_URL}/mega-bundle/status/{bundle_id}")
            
            if response.status_code == 200:
                status = response.json()
                
                if status['status'] == 'complete':
                    print(f"✅ Processing complete!")
                    return status
                elif status['status'] == 'failed':
                    print(f"❌ Processing failed: {status.get('error')}")
                    return status
                else:
                    print(f"   Status: {status['status']} - Progress: {status.get('progress', 0)}%")
                    time.sleep(5)
            else:
                print(f"❌ Status check failed: {response.status_code}")
                return None
                
        except Exception as e:
            print(f"❌ Error checking status: {e}")
            return None
    
    print("⏱️ Timeout waiting for completion")
    return None

def display_results(status):
    """Display analysis results"""
    
    if not status or 'summary' not in status:
        print("❌ No results to display")
        return
    
    summary = status['summary']
    
    print("\n" + "="*60)
    print("📊 MEGA BUNDLE ANALYSIS RESULTS")
    print("="*60)
    
    print("\n📈 Summary Metrics:")
    print(f"   Total Jobs: {summary.get('total_jobs', 0):,}")
    print(f"   Total Cost: ${summary.get('total_cost', 0):,.2f}")
    print(f"   Total Revenue: ${summary.get('total_revenue', 0):,.2f}")
    print(f"   Total Profit: ${summary.get('total_profit', 0):,.2f}")
    print(f"   Profit Margin: {summary.get('profit_margin', '0%')}")
    print(f"   Estimated Days: {summary.get('estimated_days', 0)}")
    print(f"   Labor Hours: {summary.get('total_labor_hours', 0):,.0f}")
    print(f"   Equipment Hours: {summary.get('total_equipment_hours', 0):,.0f}")
    
    # Bid recommendation (pre-bid mode)
    if 'bid_recommendation' in status:
        bid = status['bid_recommendation']
        print("\n💰 Bid Recommendation:")
        print(f"   Minimum Bid: ${bid['minimum_bid']:,.2f}")
        print(f"   Recommended Bid: ${bid['recommended_bid']:,.2f}")
        print(f"   Target Margin: {bid['target_margin']}")
        print(f"   Confidence: {bid['confidence']}")
    
    print("\n✅ Analysis complete! Full results available via API or dashboard.")

def run_complete_test():
    """Run complete test workflow"""
    
    print("🎯 MEGA BUNDLE FEATURE TEST")
    print("="*60)
    
    # Test 1: Post-win analysis (PM mode)
    print("\n📋 Test 1: Post-Win Analysis (PM Mode)")
    print("-"*40)
    status = test_upload_bundle(mode="post-win", num_jobs=50)
    if status:
        display_results(status)
    
    # Test 2: Pre-bid analysis (Bidder mode)
    print("\n\n📋 Test 2: Pre-Bid Analysis (Bidder Mode)")
    print("-"*40)
    status = test_upload_bundle(mode="pre-bid", num_jobs=50)
    if status:
        display_results(status)
    
    # Summary
    print("\n" + "="*60)
    print("✅ MEGA BUNDLE FEATURE TEST COMPLETE")
    print("="*60)
    print("\n💡 Next Steps:")
    print("1. Run the Streamlit dashboard: streamlit run mega_bundle_dashboard.py")
    print("2. Upload real job packages for production analysis")
    print("3. Export results in Excel or PDF format")
    print("4. Deploy to Render.com for production use")

def main():
    """Main test function"""
    
    # Check if API is running
    print("🔍 Checking API connection...")
    try:
        response = requests.get(f"{API_BASE_URL}/docs", timeout=5)
        if response.status_code == 200:
            print("✅ API is running")
            run_complete_test()
        else:
            print(f"❌ API returned status {response.status_code}")
            print("Please start the API first:")
            print("  cd backend/pdf-service")
            print("  python app_oct2025_enhanced.py")
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to API at", API_BASE_URL)
        print("\nTo start the system:")
        print("  cd backend/pdf-service")
        print("  python app_oct2025_enhanced.py")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()
