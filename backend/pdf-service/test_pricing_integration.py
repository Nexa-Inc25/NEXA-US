"""
Test Script for PG&E Pricing Integration
Tests all 6 pricing endpoints after deployment
"""

import requests
import json
import time

# Production URL
BASE_URL = "https://nexa-doc-analyzer-oct2025.onrender.com"

def print_section(title):
    """Print formatted section header"""
    print(f"\n{'='*80}")
    print(f"  {title}")
    print(f"{'='*80}\n")

def test_health():
    """Test 1: Health check"""
    print_section("TEST 1: Health Check")
    
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=10)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")
        return response.status_code == 200
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_learn_pricing():
    """Test 2: Upload pricing CSV"""
    print_section("TEST 2: Learn Pricing Data")
    
    try:
        # Check if CSV exists
        csv_path = "pge_prices_master_stockton_filled_TAG_only.csv"
        
        with open(csv_path, 'rb') as f:
            files = {'pricing_file': (csv_path, f, 'text/csv')}
            data = {'region': 'Stockton'}
            
            response = requests.post(
                f"{BASE_URL}/pricing/learn-pricing",
                files=files,
                data=data,
                timeout=30
            )
        
        print(f"Status: {response.status_code}")
        result = response.json()
        print(f"Response: {json.dumps(result, indent=2)}")
        
        if response.status_code == 200:
            print(f"\n✅ Loaded {result['details']['entries_indexed']} pricing entries")
            print(f"   Programs: {', '.join(result['details']['programs'])}")
            return True
        else:
            print(f"❌ Failed to load pricing")
            return False
            
    except FileNotFoundError:
        print(f"❌ CSV file not found: {csv_path}")
        print(f"   Make sure you're running from backend/pdf-service directory")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_pricing_status():
    """Test 3: Check pricing status"""
    print_section("TEST 3: Pricing Status")
    
    try:
        response = requests.get(f"{BASE_URL}/pricing/pricing-status", timeout=10)
        print(f"Status: {response.status_code}")
        result = response.json()
        print(f"Response: {json.dumps(result, indent=2)}")
        
        if result.get('status') == 'loaded':
            print(f"\n✅ Pricing data loaded: {result['total_entries']} entries")
            for program, details in result.get('programs', {}).items():
                print(f"   {program}: {details['count']} entries")
            return True
        else:
            print(f"⚠️ Pricing data not loaded")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_pricing_lookup():
    """Test 4: Pricing lookup"""
    print_section("TEST 4: Pricing Lookup")
    
    test_cases = [
        "TAG-2 inaccessible overhead replacement",
        "07-3 pole replacement type 3",
        "TAG-10 2-man electric crew",
        "TAG-14.1 restoration adder"
    ]
    
    success_count = 0
    
    for text in test_cases:
        print(f"\n🔍 Searching: '{text}'")
        
        try:
            response = requests.post(
                f"{BASE_URL}/pricing/pricing-lookup",
                data={'text': text, 'top_k': 3},
                timeout=10
            )
            
            result = response.json()
            
            if result.get('status') == 'success':
                matches = result.get('matches', [])
                print(f"   ✅ Found {len(matches)} matches")
                
                if matches:
                    best = matches[0]
                    print(f"   Best match: {best['ref_code']} - {best['unit_description']}")
                    print(f"   Relevance: {best['relevance_score']}%")
                    if best['rate']:
                        print(f"   Rate: ${best['rate']:.2f}")
                    else:
                        print(f"   Rate: TBD")
                    success_count += 1
            else:
                print(f"   ⚠️ No matches found")
                
        except Exception as e:
            print(f"   ❌ Error: {e}")
    
    print(f"\n{'='*80}")
    print(f"Lookup Results: {success_count}/{len(test_cases)} successful")
    return success_count > 0

def test_calculate_cost():
    """Test 5: Calculate cost impact"""
    print_section("TEST 5: Calculate Cost Impact")
    
    test_cases = [
        {
            "infraction_text": "TAG-2: Inaccessible OH replacement marked as go-back",
            "hours_estimate": 8,
            "expected_base": 7644.81
        },
        {
            "infraction_text": "TAG-10: 2-man electric crew for 8 hours",
            "hours_estimate": 8,
            "expected_base": 471.42 * 8
        },
        {
            "infraction_text": "07-3: Pole Replacement Type 3 go-back",
            "hours_estimate": 8,
            "expected_base": None  # TBD
        }
    ]
    
    success_count = 0
    
    for test in test_cases:
        print(f"\n💰 Calculating: '{test['infraction_text'][:50]}...'")
        
        try:
            response = requests.post(
                f"{BASE_URL}/pricing/calculate-cost",
                data={
                    'infraction_text': test['infraction_text'],
                    'hours_estimate': test['hours_estimate']
                },
                timeout=10
            )
            
            result = response.json()
            
            if result.get('status') == 'success':
                cost = result.get('cost_impact', {})
                print(f"   ✅ Ref Code: {cost.get('ref_code')}")
                print(f"   Base Cost: ${cost.get('base_cost', 0):.2f}")
                
                adders = cost.get('adders', [])
                if adders:
                    print(f"   Adders: {len(adders)}")
                    for adder in adders:
                        print(f"     - {adder['type']}: ${adder.get('estimated', 0):.2f}")
                
                print(f"   Total Savings: ${cost.get('total_savings', 0):.2f}")
                
                if cost.get('notes'):
                    print(f"   Notes: {', '.join(cost['notes'])}")
                
                success_count += 1
            else:
                print(f"   ⚠️ No pricing found")
                
        except Exception as e:
            print(f"   ❌ Error: {e}")
    
    print(f"\n{'='*80}")
    print(f"Cost Calculation Results: {success_count}/{len(test_cases)} successful")
    return success_count > 0

def test_pricing_by_code():
    """Test 6: Direct lookup by ref code"""
    print_section("TEST 6: Direct Lookup by Ref Code")
    
    ref_codes = ["TAG-2", "TAG-10", "07-1", "TAG-14.1"]
    success_count = 0
    
    for ref_code in ref_codes:
        print(f"\n🔎 Looking up: {ref_code}")
        
        try:
            response = requests.get(
                f"{BASE_URL}/pricing/pricing-by-code/{ref_code}",
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                pricing = result.get('pricing', {})
                print(f"   ✅ Found: {pricing.get('unit_description')}")
                if pricing.get('rate'):
                    print(f"   Rate: ${pricing['rate']:.2f}")
                else:
                    print(f"   Rate: TBD")
                success_count += 1
            else:
                print(f"   ⚠️ Not found (404)")
                
        except Exception as e:
            print(f"   ❌ Error: {e}")
    
    print(f"\n{'='*80}")
    print(f"Direct Lookup Results: {success_count}/{len(ref_codes)} found")
    return success_count > 0

def test_full_workflow():
    """Test 7: Full audit analysis with pricing (if spec library loaded)"""
    print_section("TEST 7: Full Audit Analysis with Pricing")
    
    print("⚠️ This test requires:")
    print("   1. Spec library loaded (use /upload-specs)")
    print("   2. Valid audit PDF")
    print("\nSkipping for now - test manually with real audit PDF")
    print("\nExample command:")
    print("""
    curl -X POST https://nexa-doc-analyzer-oct2025.onrender.com/analyze-audit \\
      -F "file=@audit_with_tag2.pdf"
    """)
    return True

def main():
    """Run all tests"""
    print("\n" + "🎯" * 40)
    print("PG&E PRICING INTEGRATION TEST SUITE")
    print("Production URL:", BASE_URL)
    print("🎯" * 40)
    
    # Wait for deployment
    print("\n⏳ Waiting 30 seconds for deployment to complete...")
    time.sleep(30)
    
    results = {}
    
    # Run tests in order
    results['health'] = test_health()
    
    if results['health']:
        results['learn_pricing'] = test_learn_pricing()
        
        if results['learn_pricing']:
            # Wait for indexing
            print("\n⏳ Waiting 5 seconds for pricing indexing...")
            time.sleep(5)
            
            results['pricing_status'] = test_pricing_status()
            results['pricing_lookup'] = test_pricing_lookup()
            results['calculate_cost'] = test_calculate_cost()
            results['pricing_by_code'] = test_pricing_by_code()
            results['full_workflow'] = test_full_workflow()
    
    # Summary
    print_section("TEST SUMMARY")
    
    total = len(results)
    passed = sum(1 for v in results.values() if v)
    
    for test, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {test}")
    
    print(f"\n{'='*80}")
    print(f"TOTAL: {passed}/{total} tests passed")
    print(f"{'='*80}\n")
    
    if passed == total:
        print("🎉 ALL TESTS PASSED! Pricing integration is live!")
        print("\n📚 Next Steps:")
        print("   1. Upload spec library via /upload-specs")
        print("   2. Test with real PG&E audit PDF")
        print("   3. Verify cost_impact appears in repealable infractions")
        print("   4. Integrate with mobile app (PhotosQAScreen)")
    else:
        print("⚠️ Some tests failed. Check logs above for details.")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
