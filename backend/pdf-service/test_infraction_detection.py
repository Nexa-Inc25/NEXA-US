#!/usr/bin/env python3
"""
Test script for infraction detection improvements
"""
import requests
import sys

ANALYZER_URL = "https://nexa-doc-analyzer-oct2025.onrender.com"

def test_analyze_audit(pdf_path):
    """Test audit analysis endpoint"""
    
    print(f"🔍 Testing infraction detection with: {pdf_path}")
    print("=" * 60)
    
    # Upload and analyze
    with open(pdf_path, 'rb') as f:
        files = {'file': (pdf_path, f, 'application/pdf')}
        
        print(f"📤 Uploading {pdf_path}...")
        response = requests.post(f"{ANALYZER_URL}/analyze-audit", files=files)
        
        if response.status_code != 200:
            print(f"❌ Error {response.status_code}: {response.text}")
            return
        
        result = response.json()
        print(f"✅ Analysis complete!\n")
        
        # Display summary
        print("📊 SUMMARY")
        print("-" * 60)
        print(f"Audit File: {result['audit_file']}")
        print(f"Spec Files Indexed: {result['total_spec_files']}")
        print(f"Spec Chunks: {result['total_spec_chunks']}")
        print(f"Infractions Found: {result['infractions_found']}")
        print(f"Infractions Analyzed: {result['infractions_analyzed']}\n")
        
        if 'summary' in result:
            summary = result['summary']
            print(f"  • Potentially Repealable: {summary['potentially_repealable']}")
            print(f"  • Valid: {summary['valid']}")
            print(f"  • High Confidence: {summary['high_confidence']}")
            print()
        
        # Display detailed results
        if 'analysis_results' in result and result['analysis_results']:
            print("📋 DETAILED RESULTS")
            print("-" * 60)
            
            for infraction in result['analysis_results'][:5]:  # Show first 5
                print(f"\n🔴 INFRACTION #{infraction['infraction_id']}")
                print(f"Status: {infraction['status']} ({infraction['confidence']} confidence)")
                print(f"Text: {infraction['infraction_text'][:150]}...")
                
                if infraction['spec_matches']:
                    print(f"\n   📚 Top {len(infraction['spec_matches'])} Spec Matches:")
                    for i, match in enumerate(infraction['spec_matches'][:3], 1):
                        print(f"   {i}. {match['source_spec']} ({match['relevance_score']}% relevant)")
                        print(f"      \"{match['spec_text'][:100]}...\"")
                else:
                    print("   ⚠️ No matching specs found")
                print()
            
            if len(result['analysis_results']) > 5:
                print(f"\n... and {len(result['analysis_results']) - 5} more infractions")
        
        elif 'message' in result:
            print(f"ℹ️  {result['message']}")
            if 'note' in result:
                print(f"   {result['note']}")
        
        print("\n" + "=" * 60)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python test_infraction_detection.py <audit_pdf_path>")
        print("\nExample:")
        print("  python test_infraction_detection.py ../test_documents/sample_audit.pdf")
        sys.exit(1)
    
    pdf_path = sys.argv[1]
    test_analyze_audit(pdf_path)
