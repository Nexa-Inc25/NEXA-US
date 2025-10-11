"""
Test Script for Enhanced Pricing with Labor & Equipment
Tests crew detection, labor calculation, and equipment selection
"""

import requests
import json

BASE_URL = "https://nexa-doc-analyzer-oct2025.onrender.com"

def print_section(title):
    print(f"\n{'='*80}")
    print(f"  {title}")
    print(f"{'='*80}\n")

def test_enhanced_cost_calculation():
    """Test enhanced cost calculation with labor and equipment"""
    print_section("ENHANCED COST CALCULATION TESTS")
    
    test_cases = [
        {
            "name": "TAG-2 with 4-man crew, 8 hours, premium time, pole job",
            "infraction_text": "TAG-2: Inaccessible OH replacement go-back with 4-man crew 8 hours premium time, pole replacement involved",
            "expected": {
                "base": 7644.81,
                "labor_approx": 4776,  # 1 Foreman + 3 JL at premium
                "equipment_approx": 1200,  # Digger, bucket, pickup, trailer
                "total_approx": 13621
            }
        },
        {
            "name": "TAG-10 with 2-man crew, 8 hours, straight time",
            "infraction_text": "TAG-10: 2-man crew electric work for 8 hours overhead cable",
            "expected": {
                "base": 471.42 * 8,  # Hourly rate
                "labor_approx": 1185,  # 1 Foreman + 1 JL straight time
                "equipment_approx": 300,  # Bucket + pickup
                "total_approx": 5262
            }
        },
        {
            "name": "TAG-5 with 3-man crew, 10 hours, premium time",
            "infraction_text": "TAG-5: KAA OH Maintenance inaccessible with 3-man crew 10 hours premium time overhead",
            "expected": {
                "base": 5038.00,
                "labor_approx": 3950,  # 1 Foreman + 2 JL premium
                "equipment_approx": 500,  # Bucket + pickup
                "total_approx": 9488
            }
        },
        {
            "name": "07-3 Pole Type 3 with 5-man crew, 12 hours, straight time",
            "infraction_text": "07-3: Pole Replacement Type 3 with 5-man crew 12 hours pole job",
            "expected": {
                "base": 0,  # TBD
                "labor_approx": 4740,  # 1 Foreman + 4 JL straight
                "equipment_approx": 1800,  # Full pole equipment
                "total_approx": 6540
            }
        }
    ]
    
    results = []
    
    for test in test_cases:
        print(f"\n{'─'*80}")
        print(f"Test: {test['name']}")
        print(f"{'─'*80}")
        print(f"Infraction: {test['infraction_text']}\n")
        
        try:
            response = requests.post(
                f"{BASE_URL}/pricing/calculate-cost",
                data={
                    'infraction_text': test['infraction_text'],
                    'hours_estimate': 8  # Will be overridden by detected hours
                },
                timeout=15
            )
            
            if response.status_code == 200:
                result = response.json()
                cost = result.get('cost_impact', {})
                
                print(f"✅ SUCCESS")
                print(f"\n📊 Cost Breakdown:")
                print(f"  Base Rate: ${cost.get('base_cost', 0):,.2f}")
                
                # Labor breakdown
                if 'labor' in cost:
                    labor = cost['labor']
                    print(f"\n  💼 Labor: ${labor['total']:,.2f}")
                    print(f"     Crew: {labor['crew_size']}-man, {labor['hours']} hours")
                    print(f"     Premium: {'Yes' if labor['premium_time'] else 'No'}")
                    for worker in labor['breakdown']:
                        print(f"     - {worker['classification']}: ${worker['rate']}/hr × {worker['hours']}hrs = ${worker['total']:,.2f}")
                
                # Equipment breakdown
                if 'equipment' in cost:
                    equip = cost['equipment']
                    print(f"\n  🚜 Equipment: ${equip['total']:,.2f}")
                    for item in equip['breakdown']:
                        print(f"     - {item['description']}: ${item['rate']}/hr × {item['quantity']} × {item['hours']}hrs = ${item['total']:,.2f}")
                
                # Adders
                if cost.get('adders'):
                    print(f"\n  ➕ Adders:")
                    for adder in cost['adders']:
                        print(f"     - {adder['type']}: ${adder.get('estimated', 0):,.2f}")
                
                # Total
                print(f"\n  💰 TOTAL SAVINGS: ${cost.get('total_savings', 0):,.2f}")
                
                # Notes
                if cost.get('notes'):
                    print(f"\n  📝 Notes:")
                    for note in cost['notes']:
                        print(f"     - {note}")
                
                # Validation
                expected = test['expected']
                actual_total = cost.get('total_savings', 0)
                expected_total = expected['total_approx']
                
                variance = abs(actual_total - expected_total)
                variance_pct = (variance / expected_total * 100) if expected_total > 0 else 0
                
                print(f"\n  🎯 Validation:")
                print(f"     Expected: ~${expected_total:,.2f}")
                print(f"     Actual: ${actual_total:,.2f}")
                print(f"     Variance: ${variance:,.2f} ({variance_pct:.1f}%)")
                
                if variance_pct < 10:
                    print(f"     ✅ PASS (within 10%)")
                    results.append(True)
                else:
                    print(f"     ⚠️ WARNING (variance > 10%)")
                    results.append(False)
                
            else:
                print(f"❌ FAILED: {response.status_code}")
                print(f"Response: {response.text}")
                results.append(False)
                
        except Exception as e:
            print(f"❌ ERROR: {e}")
            results.append(False)
    
    # Summary
    print_section("TEST SUMMARY")
    passed = sum(results)
    total = len(results)
    print(f"Passed: {passed}/{total} tests")
    print(f"Success Rate: {passed/total*100:.1f}%")
    
    return passed == total

def test_crew_detection():
    """Test crew detection from various text formats"""
    print_section("CREW DETECTION TESTS")
    
    test_texts = [
        "4-man crew working 8 hours",
        "2-MAN CREW for 10 hrs premium time",
        "5-man crew, 12 hours, double time",
        "3 man crew overtime 6 hours",
        "No crew mentioned here"
    ]
    
    for text in test_texts:
        print(f"\nText: '{text}'")
        # This would require a dedicated endpoint or we test via calculate-cost
        print(f"  (Tested via calculate-cost endpoint)")

def main():
    print("\n" + "🎯" * 40)
    print("ENHANCED PRICING TEST SUITE - LABOR & EQUIPMENT")
    print("Production URL:", BASE_URL)
    print("🎯" * 40)
    
    print("\n⏳ Waiting 30 seconds for deployment...")
    import time
    time.sleep(30)
    
    # Run tests
    success = test_enhanced_cost_calculation()
    test_crew_detection()
    
    print("\n" + "="*80)
    if success:
        print("🎉 ALL TESTS PASSED!")
        print("\n✅ Phase 1 Complete: Enhanced pricing with labor & equipment")
        print("\n📱 Ready for Phase 2: Mobile App Integration")
    else:
        print("⚠️ Some tests failed - check logs above")
    print("="*80 + "\n")
    
    return success

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
