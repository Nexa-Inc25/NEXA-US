#!/usr/bin/env python3
"""
NEXA AI As-Built Generator (Simplified)
Learns from PG&E AS-BUILT PROCEDURE 2025 to auto-generate perfect packages
"""

import json
import os
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

@dataclass
class AsBuiltComponents:
    """Components required per PG&E AS-BUILT PROCEDURE 2025"""
    ec_tag: Dict
    construction_drawing: Dict
    materials_list: Dict
    photos_section: Dict
    compliance_score: float = 0.0
    repeal_reasons: List[str] = None

class PGEAsBuiltGenerator:
    """AI-powered generator for PG&E compliant as-builts"""
    
    def __init__(self):
        self.spec_rules = {
            "digital_signatures": {
                "allowed": True,
                "reference": "Digital LAN ID acceptable per Section 4"
            },
            "photo_requirements": {
                "minimum_before": 3,
                "minimum_after": 3,
                "reference": "Page 12 - Photo documentation"
            },
            "utvac_criteria": [
                "Usable", "Traceable", "Verifiable", "Accurate", "Complete"
            ]
        }
    
    def generate_ec_tag(self, field_data: Dict) -> Dict:
        """Generate EC Tag per PG&E procedure"""
        changes = field_data.get('equipment_added') or field_data.get('equipment_removed')
        
        ec_tag = {
            "pm_number": field_data['pm_number'],
            "location": field_data.get('location_address', ''),
            "gps": field_data.get('gps', {}),
            "crew_lead": field_data.get('crew_lead', ''),
            "date_completed": datetime.now().strftime("%Y-%m-%d"),
            "construction_status": "BUILT WITH CHANGES" if changes else "BUILT AS DESIGNED",
            "fda": "N/A - No damaged equipment (Page 25)" if not field_data.get('damaged_equipment') else "Required",
            "signature": {
                "type": "Digital",
                "lan_id": field_data.get('lan_id', 'AUTO_GEN'),
                "reference": "Digital signatures acceptable per Section 4"
            }
        }
        return ec_tag
    
    def generate_construction_drawing(self, field_data: Dict) -> Dict:
        """Generate construction drawing with red-lining if needed"""
        changes = field_data.get('equipment_added') or field_data.get('equipment_removed')
        
        drawing = {
            "type": "Ad Hoc Map" if not field_data.get('drawing_number') else "Standard",
            "red_lines": {
                "status": "RED-LINED" if changes else "NO RED-LINES - BUILT AS DESIGNED",
                "reference": "Page 25" if not changes else "Pages 7-9"
            },
            "pole_location": field_data.get('pole_gps', {})
        }
        return drawing
    
    def generate_materials_list(self, field_data: Dict) -> Dict:
        """Generate materials list"""
        return {
            "items": field_data.get('materials_list', []),
            "pole_specs": {
                "class": field_data.get('pole_class', 'N/A'),
                "height": field_data.get('pole_height', 'N/A'),
                "guy_wires": "Yes - Clamped" if field_data.get('guy_wires') else "N/A"
            }
        }
    
    def generate_photos(self, field_data: Dict) -> Dict:
        """Generate photo section"""
        return {
            "before_photos": field_data.get('before_photos', []),
            "after_photos": field_data.get('after_photos', []),
            "compliance": {
                "before_count": len(field_data.get('before_photos', [])),
                "after_count": len(field_data.get('after_photos', [])),
                "meets_minimum": (
                    len(field_data.get('before_photos', [])) >= 3 and 
                    len(field_data.get('after_photos', [])) >= 3
                )
            }
        }
    
    def calculate_compliance(self, components: AsBuiltComponents) -> Tuple[float, List[str]]:
        """Calculate UTVAC compliance score"""
        score = 100.0
        reasons = []
        
        # Check photos
        if not components.photos_section['compliance']['meets_minimum']:
            score -= 20
            reasons.append("TRUE INFRACTION: Insufficient photos per Page 12")
        
        # Check signature
        if components.ec_tag['signature']['type'] == 'Digital':
            reasons.append("PASS: Digital signature acceptable per Section 4")
        
        # Check FDA
        if "N/A" in components.ec_tag.get('fda', ''):
            reasons.append("PASS: FDA not required for non-damaged equipment (Page 25)")
        
        return score / 100, reasons if score < 100 else ["Fully compliant per PG&E PROCEDURE 2025"]
    
    def generate_pdf(self, components: AsBuiltComponents, output_path: str) -> str:
        """Generate PDF package"""
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        c = canvas.Canvas(output_path, pagesize=letter)
        
        # Cover
        c.setFont("Helvetica-Bold", 20)
        c.drawString(200, 750, "AS-BUILT PACKAGE")
        c.setFont("Helvetica", 14)
        c.drawString(100, 700, f"PM: {components.ec_tag['pm_number']}")
        c.drawString(100, 680, f"Compliance: {components.compliance_score:.1%}")
        
        # EC Tag
        c.showPage()
        c.setFont("Helvetica-Bold", 16)
        c.drawString(100, 750, "ELECTRIC CONSTRUCTION TAG")
        c.setFont("Helvetica", 12)
        y = 700
        for key, value in components.ec_tag.items():
            if isinstance(value, dict):
                value = json.dumps(value)
            c.drawString(100, y, f"{key}: {value}")
            y -= 20
        
        # Construction Drawing
        c.showPage()
        c.setFont("Helvetica-Bold", 16)
        c.drawString(100, 750, "CONSTRUCTION DRAWING")
        c.setFont("Helvetica", 12)
        c.drawString(100, 700, f"Status: {components.construction_drawing['red_lines']['status']}")
        
        # Materials
        c.showPage()
        c.setFont("Helvetica-Bold", 16)
        c.drawString(100, 750, "MATERIALS LIST")
        c.setFont("Helvetica", 12)
        y = 700
        for item in components.materials_list['items']:
            c.drawString(100, y, f"- {item['name']}: {item['quantity']} @ ${item['cost']}")
            y -= 20
        
        # Photos
        c.showPage()
        c.setFont("Helvetica-Bold", 16)
        c.drawString(100, 750, "PHOTO DOCUMENTATION")
        c.setFont("Helvetica", 12)
        c.drawString(100, 700, f"Before: {components.photos_section['compliance']['before_count']} photos")
        c.drawString(100, 680, f"After: {components.photos_section['compliance']['after_count']} photos")
        
        c.save()
        return output_path
    
    def generate_asbuilt(self, field_data: Dict) -> Tuple[AsBuiltComponents, str]:
        """Generate complete as-built package"""
        
        # Generate components
        components = AsBuiltComponents(
            ec_tag=self.generate_ec_tag(field_data),
            construction_drawing=self.generate_construction_drawing(field_data),
            materials_list=self.generate_materials_list(field_data),
            photos_section=self.generate_photos(field_data)
        )
        
        # Calculate compliance
        components.compliance_score, components.repeal_reasons = self.calculate_compliance(components)
        
        # Generate PDF
        output_path = f"generated_asbuilts/{field_data['pm_number']}_asbuilt.pdf"
        self.generate_pdf(components, output_path)
        
        return components, output_path

# Export for test script
__all__ = ['PGEAsBuiltGenerator', 'AsBuiltComponents']
