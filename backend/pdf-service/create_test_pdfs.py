#!/usr/bin/env python3
"""
Create test PDFs for electrical spec analyzer testing
"""

from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.utils import simpleSplit
import os

def create_spec_pdf(filename="test_spec.pdf"):
    """Create a test specification PDF with electrical standards"""
    c = canvas.Canvas(filename, pagesize=letter)
    width, height = letter
    
    # Page 1: Title and Overview
    c.setFont("Helvetica-Bold", 16)
    c.drawString(100, height - 50, "PG&E Electrical Specifications Manual")
    c.setFont("Helvetica", 12)
    
    spec_text = """
    Section 1: General Requirements
    
    All electrical installations shall comply with:
    - GO 95 (General Order 95) - Rules for overhead electric line construction
    - GO 128 - Rules for underground electric supply
    - CPUC regulations for utility infrastructure
    - ANSI C37.60 for high-voltage equipment
    - IEEE 1547 for interconnection standards
    - NEC Article 250 for grounding requirements
    - NESC standards for clearances
    
    Section 2: Equipment Standards
    
    2.1 Insulators
    - 12kV insulators must meet ANSI C29.1 standards
    - Minimum creepage distance: 10 inches
    - Material: Porcelain or polymer composite
    
    2.2 Conductors
    - 336.4 MCM AAC for primary distribution
    - 4/0 ACSR for secondary lines
    - Minimum clearance: 8 feet from structures
    
    2.3 Transformers
    - Single-phase units: 10kVA to 167kVA
    - Three-phase units: 30kVA to 750kVA
    - Must comply with IEEE C57.12.00
    
    Section 3: Installation Requirements
    
    3.1 Pole Installation
    - Grade B construction required for highway crossings
    - Minimum pole depth: 10% of pole length plus 2 feet
    - Crossarm height: minimum 25 feet from ground
    
    3.2 Underground Installation
    - Trench depth: 48 inches for primary conduit
    - 36 inches for secondary conduit
    - Warning tape at 12 inches below grade
    
    3.3 Clearances (per GO 95)
    - Vertical clearance over roads: 18 feet minimum
    - Horizontal clearance from buildings: 7.5 feet
    - Phase-to-phase spacing: 12 inches at 12kV
    
    Section 4: Testing Requirements
    
    4.1 Insulation Testing
    - Megger test at 5000V for cable insulation
    - Minimum resistance: 100 megohms
    
    4.2 Grounding Tests
    - Ground resistance not to exceed 25 ohms
    - Annual testing required
    """
    
    y_position = height - 100
    for line in spec_text.split('\n'):
        if y_position < 50:  # New page if needed
            c.showPage()
            c.setFont("Helvetica", 12)
            y_position = height - 50
        
        # Handle section headers
        if line.strip().startswith('Section'):
            c.setFont("Helvetica-Bold", 14)
        elif line.strip() and line[0].isdigit() and '.' in line[:4]:
            c.setFont("Helvetica-Bold", 12)
        else:
            c.setFont("Helvetica", 11)
        
        c.drawString(72, y_position, line.strip())
        y_position -= 15
    
    c.save()
    print(f"Created {filename}")
    return filename

def create_audit_pdf(filename="test_audit.pdf"):
    """Create a test audit PDF with infractions"""
    c = canvas.Canvas(filename, pagesize=letter)
    width, height = letter
    
    # Page 1: Audit Report
    c.setFont("Helvetica-Bold", 16)
    c.drawString(100, height - 50, "Electrical Infrastructure Audit Report")
    c.setFont("Helvetica", 12)
    c.drawString(100, height - 70, "Date: October 11, 2025")
    c.drawString(100, height - 90, "Location: District 7, Northern California")
    
    audit_text = """
    EXECUTIVE SUMMARY
    
    This audit identified multiple non-compliance issues with electrical 
    infrastructure standards. The following go-back infractions were documented:
    
    FINDINGS AND INFRACTIONS
    
    Go-back Infraction: Crossarm mounted at 20 inches from pole top violating 
    GO 95 minimum clearance requirements of 25 feet from ground level. This 
    poses safety risks and must be corrected within 30 days.
    
    Go-back Infraction: Underground conduit installed at 36 inches depth in 
    primary voltage area. Standards require 48 inches minimum depth per 
    Document 093412 and CPUC regulations for primary installations.
    
    Go-back Infraction: 4/0 ACSR conductor used in area requiring 336.4 MCM 
    AAC per GO 95 Rule 31.2 for the measured span length and loading conditions.
    
    Go-back Infraction: Insulator creepage distance measured at 7 inches, 
    below the required 10 inches minimum per ANSI C29.1 for 12kV systems 
    in contamination zone III.
    
    Go-back Infraction: Ground resistance measured at 45 ohms, exceeding the 
    25 ohm maximum requirement. This violates NEC Article 250 and creates 
    dangerous step potential conditions.
    
    Go-back Infraction: Missing bird guard protection on 15kV equipment. 
    ANSI C37.60 requires wildlife protectors on all exposed energized parts 
    above 15kV in designated avian areas.
    
    COMPLIANT ITEMS
    
    The following items were found to be compliant:
    - Transformer installations meet IEEE C57.12.00 requirements
    - Warning tape properly installed at 12 inches below grade
    - Phase-to-phase spacing adequate at 12 inches for 12kV
    
    RECOMMENDATIONS
    
    1. Immediate correction of crossarm height violation (Priority: High)
    2. Re-trench primary conduit to proper 48-inch depth (Priority: High)  
    3. Replace undersized conductors with proper 336.4 MCM AAC (Priority: Medium)
    4. Replace non-compliant insulators (Priority: Medium)
    5. Install additional grounding rods to reduce resistance (Priority: High)
    6. Install bird guards on all high-voltage equipment (Priority: Low)
    
    CONCLUSION
    
    Six critical infractions require immediate attention. All violations 
    reference specific standards (GO 95, CPUC, ANSI) that can be cross-
    referenced with the current specification manual for compliance verification.
    """
    
    y_position = height - 120
    for line in audit_text.split('\n'):
        if y_position < 50:  # New page if needed
            c.showPage()
            c.setFont("Helvetica", 12)
            y_position = height - 50
        
        # Handle headers
        if line.strip().isupper() and len(line.strip()) > 3:
            c.setFont("Helvetica-Bold", 13)
        elif line.strip().startswith('Go-back Infraction:'):
            c.setFont("Helvetica-Bold", 11)
        else:
            c.setFont("Helvetica", 11)
        
        # Word wrap long lines
        if len(line) > 80:
            lines = simpleSplit(line, "Helvetica", 11, width - 144)
            for wrapped_line in lines:
                c.drawString(72, y_position, wrapped_line)
                y_position -= 14
        else:
            c.drawString(72, y_position, line.strip())
            y_position -= 14
    
    c.save()
    print(f"Created {filename}")
    return filename

if __name__ == "__main__":
    print("Creating test PDFs for electrical analyzer...")
    
    # Create both PDFs
    spec_file = create_spec_pdf()
    audit_file = create_audit_pdf()
    
    print(f"\n✅ Test PDFs created successfully!")
    print(f"   - Specification: {spec_file}")
    print(f"   - Audit Report: {audit_file}")
    print("\nThese PDFs contain:")
    print("- Electrical standards (GO 95, CPUC, ANSI, IEEE, NEC, NESC)")
    print("- Equipment specs (insulators, conductors, transformers)")
    print("- 6 go-back infractions that reference standards")
    print("\nUse these to test the /upload_spec and /upload_audit endpoints!")
