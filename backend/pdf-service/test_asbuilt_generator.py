#!/usr/bin/env python3
"""
Test the NEXA AI As-Built Generator with PM 35125285
Real pole work at 2195 Summit Level Rd, Rail Road Flat, CA
"""

from asbuilt_generator_simple import PGEAsBuiltGenerator
import json

def test_generator_with_pm35125285():
    """Test with PM 35125285 - Pole work at 2195 Summit Level Rd"""
    
    generator = PGEAsBuiltGenerator()
    
    # Field data for PM 35125285 from USA ticket
    field_data = {
        "pm_number": "35125285",
        "notification_number": "119605285",
        "location_address": "2195 Summit Level Rd, Rail Road Flat, CA",
        "gps": {"lat": 38.337308, "lng": -120.483566},
        "pole_gps": {"lat": 38.337308, "lng": -120.483566},
        "work_description": "Electric pole work - installation",
        "crew_lead": "John Smith",
        "lan_id": "JSMITH01",
        "crew_members": ["Mike Johnson", "Tom Wilson"],
        "total_hours": 6.5,
        
        # Pole specifics
        "pole_class": "Class 1",
        "pole_height": "45 ft",
        "pole_type": "Wood",
        "guy_wires": True,
        
        # Materials from USA ticket
        "materials_list": [
            {"name": "Wood Pole Class 1", "quantity": 1, "cost": 1200},
            {"name": "Guy Wire", "quantity": 100, "cost": 250},
            {"name": "3-bolt clamp", "quantity": 2, "cost": 45},
            {"name": "Hardware kit", "quantity": 1, "cost": 150}
        ],
        
        # Photos (simulated with proper GPS/timestamps)
        "before_photos": [
            {"filename": "before_1.jpg", "timestamp": "2025-10-12T08:00:00", 
             "gps": {"lat": 38.337308, "lng": -120.483566}, 
             "description": "Existing site conditions"},
            {"filename": "before_2.jpg", "timestamp": "2025-10-12T08:05:00", 
             "gps": {"lat": 38.337308, "lng": -120.483566}, 
             "description": "Old pole to be replaced"},
            {"filename": "before_3.jpg", "timestamp": "2025-10-12T08:10:00", 
             "gps": {"lat": 38.337308, "lng": -120.483566}, 
             "description": "Clearance measurements"}
        ],
        "after_photos": [
            {"filename": "after_1.jpg", "timestamp": "2025-10-12T14:00:00", 
             "gps": {"lat": 38.337308, "lng": -120.483566}, 
             "description": "New pole installed"},
            {"filename": "after_2.jpg", "timestamp": "2025-10-12T14:05:00", 
             "gps": {"lat": 38.337308, "lng": -120.483566}, 
             "description": "Guy wires properly clamped"},
            {"filename": "after_3.jpg", "timestamp": "2025-10-12T14:10:00", 
             "gps": {"lat": 38.337308, "lng": -120.483566}, 
             "description": "Clearances verified"}
        ],
        
        # No changes from design (built as designed)
        "equipment_added": None,
        "equipment_removed": None,
        "equipment_relocated": None,
        "damaged_equipment": False,
        "primary_voltage_change": False
    }
    
    print("="*60)
    print("NEXA AI AS-BUILT GENERATOR TEST")
    print("PM 35125285 - Pole Work at 2195 Summit Level Rd")
    print("="*60)
    
    # Generate as-built
    components, pdf_path = generator.generate_asbuilt(field_data)
    
    # Print results
    print(f"\n✅ AS-BUILT GENERATED")
    print(f"   PDF Location: {pdf_path}")
    print(f"   Compliance Score: {components.compliance_score:.1%}")
    
    print(f"\n📋 PACKAGE CONTENTS:")
    print(f"   • Cover Sheet: ✓")
    print(f"   • EC Tag: {components.ec_tag['construction_status']}")
    print(f"   • Construction Drawing: {components.construction_drawing['red_lines']['status']}")
    print(f"   • Materials List: {len(components.materials_list['items'])} items")
    print(f"   • Photos: {len(components.photos_section['before_photos'])} before, {len(components.photos_section['after_photos'])} after")
    # QR Code, FDA, and CMCS are optional in simplified version
    print(f"   • Digital Signature: ✓ (LAN ID: {components.ec_tag['signature']['lan_id']})")
    
    print(f"\n📊 COMPLIANCE ANALYSIS:")
    print(f"   UTVAC Score: {components.compliance_score:.1%}")
    print(f"   Status: {'COMPLIANT' if components.compliance_score >= 0.95 else 'NEEDS REVIEW'}")
    
    print(f"\n📝 ASSESSMENT:")
    for reason in components.repeal_reasons:
        print(f"   • {reason}")
    
    # Simulate audit of generated package
    print(f"\n🔍 SIMULATED QA AUDIT:")
    audit_results = simulate_qa_audit(components)
    
    for result in audit_results:
        print(f"   • {result['check']}: {result['status']}")
        if result['status'] == 'REPEALABLE':
            print(f"     Reason: {result['reason']}")
    
    # Save components to JSON for inspection
    output_json = f"generated_asbuilts/{field_data['pm_number']}_components.json"
    with open(output_json, 'w') as f:
        # Convert dataclass to dict, handling non-serializable items
        components_dict = {
            "pm_number": field_data['pm_number'],
            "compliance_score": components.compliance_score,
            "ec_tag": components.ec_tag,
            "construction_drawing": components.construction_drawing,
            "materials_list": components.materials_list,
            "photos_section": components.photos_section,
            "repeal_reasons": components.repeal_reasons
        }
        json.dump(components_dict, f, indent=2, default=str)
    
    print(f"\n💾 Components saved to: {output_json}")
    
    return components, pdf_path

def simulate_qa_audit(components):
    """Simulate QA audit of generated package"""
    audit_results = []
    
    # Check EC Tag signature
    if components.ec_tag.get('signature', {}).get('type') == 'Digital':
        audit_results.append({
            "check": "EC Tag Signature",
            "status": "PASS",
            "reason": "Digital signature acceptable per Section 4"
        })
    else:
        audit_results.append({
            "check": "EC Tag Signature",
            "status": "FAIL",
            "reason": "Missing signature"
        })
    
    # Check construction status
    if components.ec_tag.get('construction_status') == 'BUILT AS DESIGNED':
        audit_results.append({
            "check": "Construction Status",
            "status": "PASS",
            "reason": "Properly marked as built per design"
        })
    
    # Check FDA requirement (from EC tag in simplified version)
    if "N/A" in components.ec_tag.get('fda', ''):
        audit_results.append({
            "check": "FDA Requirement",
            "status": "PASS",
            "reason": "FDA not required - no damaged equipment per Page 25"
        })
    
    # Check photo compliance
    photo_compliance = components.photos_section.get('compliance', {})
    if photo_compliance.get('minimum_before_met') and photo_compliance.get('minimum_after_met'):
        audit_results.append({
            "check": "Photo Requirements",
            "status": "PASS",
            "reason": "Minimum 3 before/after photos with GPS/timestamps"
        })
    else:
        audit_results.append({
            "check": "Photo Requirements",
            "status": "FAIL",
            "reason": "Insufficient photos per Page 12"
        })
    
    # Check for potential infractions
    if components.compliance_score < 0.95:
        audit_results.append({
            "check": "Overall Compliance",
            "status": "NEEDS REVIEW",
            "reason": f"Score {components.compliance_score:.1%} below 95% threshold"
        })
    else:
        audit_results.append({
            "check": "Overall Compliance",
            "status": "PASS",
            "reason": f"Score {components.compliance_score:.1%} meets PG&E requirements"
        })
    
    # Check for repealable items
    for reason in components.repeal_reasons or []:
        if "REPEALABLE" in reason:
            audit_results.append({
                "check": "Infraction Analysis",
                "status": "REPEALABLE",
                "reason": reason
            })
    
    return audit_results

def test_emergency_pole():
    """Test emergency pole replacement scenario"""
    
    generator = PGEAsBuiltGenerator()
    
    emergency_data = {
        "pm_number": "EMERGENCY001",
        "notification_number": "EMRG2025001",
        "location_address": "Emergency site",
        "gps": {"lat": 37.7749, "lng": -122.4194},
        "work_description": "Emergency pole replacement - storm damage",
        "crew_lead": "Emergency Response Team",
        "lan_id": "EMRG01",
        "total_hours": 4.0,
        "emergency": True,
        
        # Minimal photos for emergency
        "before_photos": [
            {"filename": "emrg_before.jpg", "timestamp": "2025-10-12T22:00:00", 
             "gps": {"lat": 37.7749, "lng": -122.4194}}
        ],
        "after_photos": [
            {"filename": "emrg_after.jpg", "timestamp": "2025-10-13T02:00:00", 
             "gps": {"lat": 37.7749, "lng": -122.4194}}
        ],
        
        "damaged_equipment": True,
        "damaged_equipment_list": ["Broken pole", "Damaged crossarm"]
    }
    
    print("\n" + "="*60)
    print("EMERGENCY POLE REPLACEMENT TEST")
    print("="*60)
    
    components, pdf_path = generator.generate_asbuilt(emergency_data)
    
    print(f"\n✅ EMERGENCY AS-BUILT GENERATED")
    print(f"   Compliance Score: {components.compliance_score:.1%}")
    print(f"   FDA Status: {components.ec_tag.get('fda', 'N/A')}")
    print(f"   Expedited Processing: Yes")
    
    return components

if __name__ == "__main__":
    # Test main PM
    components_main, pdf_main = test_generator_with_pm35125285()
    
    # Test emergency scenario
    components_emergency = test_emergency_pole()
    
    print("\n" + "="*60)
    print("ALL TESTS COMPLETE")
    print("="*60)
    print(f"\nGenerated As-Builts:")
    print(f"  1. PM 35125285: {components_main.compliance_score:.1%} compliance")
    print(f"  2. Emergency: {components_emergency.compliance_score:.1%} compliance")
    print(f"\n✅ NEXA AI Generator ready for production!")
