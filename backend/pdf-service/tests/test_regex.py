#!/usr/bin/env python3
"""
Test script for optimized regex patterns
Demonstrates multi-line extraction capabilities
"""

import re

# Optimized regex patterns - improved for complete capture
# Captures full document names (stops at dash for description)
BULLET_REGEX = r'[·•\-\*]\s*([A-Z][A-Z\s&]+?)(?:\s*[-–—]\s*|\n(?=[·•\-\*])|$)'
# For numbered items with multi-line support
NUMBERED_REGEX = r'(\d+)\.\s*([^\n]+(?:\n\s+[^\n\d]+)*)'
# Infraction patterns - working well for multi-line
INFRACTION_REGEX = r'(?i)(go-back|infraction|violation|issue|problem|deficiency|non-compliance):\s*([^\n]+(?:\n(?!(?:go-back|infraction|violation|issue|problem|deficiency|non-compliance):)[^\n]+)*)'

# Test document with multi-line content
test_document = """
AS-BUILT ORDER

The following documents must be included in the as-built package:

· POLE BILL - Contains all pole specifications and
  loading calculations for the installation
· EC TAG - Environmental compliance documentation
  including permits and approvals from local authorities
· PG&E FACE SHEET - Primary document showing
  customer information and job details
· EQUIPMENT & POLE INFORMATION - Detailed specs for
  all equipment installed including serial numbers
  and manufacturer data
· CONSTRUCTION FEEDBACK - Field notes and changes
  made during construction phase
· CREW INSTRUCTIONS - Step-by-step procedures
  followed by the crew
· CREW MATERIALS - Complete list of materials
  used in the job
· MAP - Geographic location and route details
· JP FORMS - Job package forms required by PG&E
· CCSC - California Contractor State Certification

CREW MATERIALS

Item                    Quantity        Location
Bolts (5/8" x 12")     25              Yard A-3
Wire (12 AWG)          500 ft          Truck 2
Insulators             15              Warehouse B
Ground Rods            8               Field Stock
Safety Equipment       1 set           Personal Issue

CREW INSTRUCTIONS

1. Verify all permits are in place before
   beginning any work on site
2. Conduct safety briefing with all crew members
   including review of hazards and emergency procedures
3. Install ground rods at designated locations
   ensuring proper depth and connection
4. Mount equipment per manufacturer specifications
   with attention to torque requirements
5. Complete all connections following PG&E
   standard practices and procedures

AUDIT FINDINGS

Go-back Infraction: Missing safety barriers at pole location
Details: Crew failed to install proper barriers around work area
as required by section 4.2.1 of safety manual

Violation: Incorrect wire gauge used (14 AWG instead of 12 AWG)
Specifications clearly state minimum 12 AWG for this application
per PG&E standard 2025-03

Issue: Failed to install proper grounding as per specification
Ground resistance measured at 35 ohms, requirement is maximum 25 ohms
This must be corrected before energization

Problem: Insufficient clearance between conductors
Found 3 feet clearance, minimum requirement is 4 feet
per CPUC General Order 95 Rule 37

Non-compliance: No permit documentation provided for work performed
All work requires valid permit per local ordinance 2025.14
Permit must be obtained retroactively
"""

def test_as_built_extraction():
    """Test extraction of AS-BUILT ORDER list"""
    print("=== Testing AS-BUILT ORDER Extraction ===\n")
    
    # Extract AS-BUILT ORDER section
    order_match = re.search(r'AS[\-\s]?BUILT ORDER[:\s]*(.*?)(?=\nCREW|\n\n[A-Z]{4,}|\Z)', test_document, re.IGNORECASE | re.DOTALL)
    if order_match:
        order_section = order_match.group(1)
        
        # Extract bullet items (handles multi-line)
        bullet_items = re.findall(BULLET_REGEX, order_section, re.MULTILINE)
        
        print(f"Found {len(bullet_items)} required documents:")
        for i, item in enumerate(bullet_items, 1):
            cleaned = item.strip().replace('\n', ' ').replace('  ', ' ')
            # Extract just the document name (before dash)
            doc_name = cleaned.split(' - ')[0] if ' - ' in cleaned else cleaned
            print(f"  {i}. {doc_name}")
        print()

def test_materials_extraction():
    """Test extraction of CREW MATERIALS"""
    print("=== Testing CREW MATERIALS Extraction ===\n")
    
    # Extract CREW MATERIALS section
    section_match = re.search(r'CREW MATERIALS[:\s]*(.*?)(?=\nCREW INSTRUCTIONS|\n[A-Z]{4,}[\s:]|\Z)', test_document, re.IGNORECASE | re.DOTALL)
    if section_match:
        section_text = section_match.group(1)
        lines = section_text.strip().split('\n')
        
        # Detect table structure - look for consistent spacing
        table_data = []
        for line in lines:
            # More flexible table detection
            if line.strip() and (re.search(r'\s{2,}', line) or '\t' in line):
                # Split by multiple spaces or tabs
                cols = re.split(r'\s{2,}|\t', line)
                cols = [c.strip() for c in cols if c.strip()]
                if cols:
                    table_data.append(cols)
        
        if table_data:
            print("Materials Table Detected:")
            print(f"  Headers: {table_data[0]}")
            print(f"  Total rows: {len(table_data)-1}")
            print("  Sample rows:")
            for i, row in enumerate(table_data[1:6], 1):  # Show first 5 data rows
                print(f"    {i}. {row}")
        else:
            print("No table structure detected in materials section")
        print()

def test_instructions_extraction():
    """Test extraction of CREW INSTRUCTIONS"""
    print("=== Testing CREW INSTRUCTIONS Extraction ===\n")
    
    # Extract CREW INSTRUCTIONS section  
    section_match = re.search(r'CREW INSTRUCTIONS[:\s]*(.*?)(?=\nAUDIT|\n[A-Z]{4,}[\s:]|\Z)', test_document, re.IGNORECASE | re.DOTALL)
    if section_match:
        section_text = section_match.group(1)
        
        # Extract numbered items (handles multi-line)
        numbered = re.findall(NUMBERED_REGEX, section_text, re.MULTILINE)
        
        if numbered:
            print(f"Found {len(numbered)} instructions:")
            for num, item in numbered:
                cleaned = item.strip().replace('\n', ' ').replace('  ', ' ')
                preview = cleaned[:100] + "..." if len(cleaned) > 100 else cleaned
                print(f"  {num}. {preview}")
        else:
            # Try simpler pattern for numbered items
            simple_numbered = re.findall(r'(\d+)\.\s*([^\n]+)', section_text)
            if simple_numbered:
                print(f"Found {len(simple_numbered)} instructions (simple pattern):")
                for num, item in simple_numbered[:5]:
                    print(f"  {num}. {item[:80]}...")
        print()

def test_infraction_extraction():
    """Test extraction of infractions with multi-line descriptions"""
    print("=== Testing Infraction Extraction (Multi-line) ===\n")
    
    # Extract infractions using optimized regex
    infractions = re.findall(INFRACTION_REGEX, test_document, re.MULTILINE | re.DOTALL)
    
    print(f"Found {len(infractions)} infractions:")
    for i, (type, description) in enumerate(infractions, 1):
        # Clean multi-line description
        cleaned_desc = re.sub(r'\s*\n\s*', ' ', description.strip())
        cleaned_desc = re.sub(r'\s+', ' ', cleaned_desc)
        
        preview = cleaned_desc[:150] + "..." if len(cleaned_desc) > 150 else cleaned_desc
        print(f"\n  {i}. {type.upper()}: {preview}")
    print()

def main():
    print("=" * 60)
    print("Optimized Regex Pattern Testing")
    print("=" * 60)
    print()
    
    test_as_built_extraction()
    test_materials_extraction()
    test_instructions_extraction()
    test_infraction_extraction()
    
    print("=" * 60)
    print("✓ All pattern tests completed")
    print("=" * 60)

if __name__ == "__main__":
    main()
