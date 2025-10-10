"""
PG&E As-Built Procedure Processor
Implements intelligent filling, document pairing, and pricing based on PG&E standards
Enhanced with pole classification and document ordering
"""
import json
import re
import io
from typing import Dict, List, Optional, Tuple
import PyPDF2
from reportlab.pdfgen import canvas
from reportlab.lib.colors import red, blue, black
from reportlab.lib.pagesizes import letter
from pole_classifier import PoleClassifier
from document_ordering import DocumentOrderingSystem
import logging

logger = logging.getLogger(__name__)

class PGEAsBuiltProcessor:
    """Process as-builts according to PG&E 2025 procedures"""
    
    def __init__(self, data_path="/data"):
        self.data_path = data_path
        self.rules = self.load_rules()
        self.mat_prices = self.load_mat_prices()
        self.pole_classifier = PoleClassifier()
        self.doc_ordering = DocumentOrderingSystem(data_path)
        
    def load_rules(self) -> Dict:
        """Load extracted PG&E rules from persistent storage"""
        try:
            with open(f'{self.data_path}/asbuilt_rules.json', 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            return self.default_rules()
    
    def default_rules(self) -> Dict:
        """Default PG&E rules extracted from procedure PDF"""
        return {
            'red_line': {
                'purpose': 'Changes and modifications',
                'actions': [
                    'Strike through items not installed',
                    'Write specific changes made',
                    'Circle and annotate field modifications'
                ]
            },
            'blue_line': {
                'purpose': 'Notes and additional information',
                'actions': [
                    'Add FIF (Found In Field) notes',
                    'Document FCOA (Field Change Order Authorization)',
                    'Add clarifying comments'
                ]
            },
            'pairing_table': {
                'Planned Estimated': [
                    'EC Tag', 'Construction Drawing', 'Key Sketch', 
                    'Crew Instructions', 'Crew Materials List', 'CFSS',
                    'Pole Equipment Form', 'CMCS', 'Form 23', 'Form 48',
                    'FAS Screen Capture'
                ],
                'Routine Emergency Estimated': [
                    'EC Tag', 'Construction Drawing', 'Crew Instructions',
                    'Crew Materials List', 'CFSS', 'Pole Equipment Form',
                    'CMCS', 'Form 23', 'Form 48'
                ],
                'Planned WRG': [
                    'Construction Drawing', 'Key Sketch', 'WRG Form',
                    'Crew Instructions', 'Crew Materials List', 'CFSS',
                    'Pole Equipment Form', 'CMCS', 'Form 23', 'Form 48'
                ],
                'Emergency Unit Completion': [
                    'Unit Completion Report', 'Switching Summary',
                    'Safety Documentation', 'Photos'
                ]
            },
            'fda': {
                'requirement': 'Add FDAs to Field Comments',
                'action': 'Upload EC Tag to SAP after completion'
            },
            'cert_sheet': {
                'template': 'Field Verification Certification Sheet',
                'required_fields': [
                    'Job Number (PM/Notification)',
                    'Built As Designed (Yes/No)',
                    'If No, explain changes',
                    'LAN ID',
                    'Date',
                    'Signature'
                ]
            }
        }
    
    def extract_asbuilt_rules(self, pdf_text: str, filename: Optional[str] = None) -> Dict:
        """Extract rules from uploaded PG&E procedure PDF"""
        rules = self.default_rules()
        
        # Parse Section 3: Marking Up Documents
        if "Marking Up Documents" in pdf_text:
            marking_section = self.extract_section(pdf_text, "Marking Up Documents")
            if "red pen" in marking_section.lower():
                rules['red_line']['extracted'] = self.parse_red_line_rules(marking_section)
            if "blue" in marking_section.lower() or "black" in marking_section.lower():
                rules['blue_line']['extracted'] = self.parse_blue_line_rules(marking_section)
        
        # Parse Table 3: As-Built Package by Work Type
        if "As-Built Package by Work Type" in pdf_text:
            table_section = self.extract_section(pdf_text, "Table 3")
            rules['pairing_table'] = self.parse_pairing_table(table_section)
        
        # Parse Section 10: FDA Handling
        if "EC Notification As-Built FDA" in pdf_text:
            fda_section = self.extract_section(pdf_text, "FDA")
            rules['fda']['details'] = self.parse_fda_requirements(fda_section)
        
        # Handle new spec PDFs
        if filename:
            # Document ordering PDF
            if "document order" in filename.lower():
                doc_order = self.doc_ordering.extract_document_order(pdf_text)
                rules['document_order'] = doc_order
                logger.info(f"Extracted document order: {len(doc_order)} documents")
            
            # Pole types PDF
            if "pole types" in filename.lower():
                rules['pole_types'] = self.extract_pole_types(pdf_text)
                logger.info(f"Extracted pole type specifications")
        
        # Save to persistent storage
        with open(f'{self.data_path}/asbuilt_rules.json', 'w') as f:
            json.dump(rules, f, indent=2)
        
        logger.info(f"Extracted and saved PG&E rules from procedure PDF")
        return rules
    
    def extract_section(self, text: str, section_name: str) -> str:
        """Extract a specific section from the PDF text"""
        # Simple extraction - can be enhanced with better parsing
        start_idx = text.find(section_name)
        if start_idx == -1:
            return ""
        # Find next section or take 2000 chars
        end_idx = min(start_idx + 2000, len(text))
        return text[start_idx:end_idx]
    
    def parse_red_line_rules(self, text: str) -> List[str]:
        """Parse red-lining rules from text"""
        rules = []
        patterns = [
            r'red.*?strike.*?through',
            r'red.*?changes',
            r'red.*?not installed',
            r'red.*?modifications'
        ]
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            rules.extend(matches)
        return rules
    
    def parse_blue_line_rules(self, text: str) -> List[str]:
        """Parse blue-lining rules from text"""
        rules = []
        patterns = [
            r'blue.*?notes',
            r'blue.*?FIF',
            r'blue.*?FCOA',
            r'black.*?comments'
        ]
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            rules.extend(matches)
        return rules
    
    def parse_pairing_table(self, text: str) -> Dict[str, List[str]]:
        """Parse document pairing table from text"""
        # This would need more sophisticated parsing for actual table
        # For now, return enhanced default
        return self.default_rules()['pairing_table']
    
    def parse_fda_requirements(self, text: str) -> str:
        """Parse FDA handling requirements"""
        fda_patterns = [
            r'FDA.*?Field Comments',
            r'upload.*?EC Tag.*?SAP',
            r'Field.*?Data.*?Attachment'
        ]
        requirements = []
        for pattern in fda_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            requirements.extend(matches)
        return "; ".join(requirements)
    
    def extract_pole_types(self, text: str) -> Dict:
        """Extract pole type information from PDF"""
        pole_info = {
            'types': {},
            'examples': {},
            'notes': '',
            'pricing_guidance': {}
        }
        
        # Extract type definitions
        type_patterns = [
            r'Type\s*(\d).*?(?:Easy|Moderate|Medium|Difficult|Bid)',
            r'(\d)\s*(?:Primary|level)',
        ]
        
        # Extract notes section
        if 'Notes' in text:
            notes_match = re.search(r'Notes[:\s]+(.*?)(?:\n\n|$)', text, re.DOTALL)
            if notes_match:
                pole_info['notes'] = notes_match.group(1).strip()
        
        # Store extracted info
        return pole_info
    
    def determine_work_type(self, job_data: Dict) -> str:
        """Determine work type from job data"""
        # Check job fields for work type indicators
        job_text = str(job_data).lower()
        
        if 'emergency' in job_text:
            if 'unit completion' in job_text:
                return 'Emergency Unit Completion'
            return 'Routine Emergency Estimated'
        elif 'wrg' in job_text:
            return 'Planned WRG'
        elif 'planned' in job_text:
            return 'Planned Estimated'
        else:
            return 'Planned Estimated'  # Default
    
    def fill_asbuilt(self, pdf_content: bytes, job_data: Dict, 
                     photos: Optional[List[str]] = None) -> Dict:
        """
        Intelligently fill as-built based on PG&E rules
        Returns filled PDF with annotations and metadata
        Enhanced with pole classification and document ordering
        """
        # Extract text from PDF
        text = self.extract_pdf_text(pdf_content)
        
        # Determine work type
        work_type = self.determine_work_type(job_data)
        
        # Classify pole type from text and photos
        pole_type, pole_confidence, pole_reason = self.pole_classifier.classify_pole(text, photos)
        
        # Get required documents based on work type AND pole type
        required_docs = self.doc_ordering.get_required_documents(work_type, pole_type)
        
        # Sort documents in PG&E standard order
        ordered_docs = self.doc_ordering.sort_documents(required_docs, work_type, pole_type)
        
        # Extract material codes
        mat_codes = self.extract_mat_codes(text)
        
        # Calculate pricing with pole type adjustment
        base_pricing = self.calculate_pricing(mat_codes)
        adjusted_price, price_calc = self.pole_classifier.calculate_adjusted_price(
            base_pricing['total'], pole_type
        )
        
        # Update pricing with pole adjustment
        pricing = {
            **base_pricing,
            'adjusted_total': adjusted_price,
            'pole_adjustment': price_calc,
            'pole_type': pole_type
        }
        
        # Generate fill suggestions
        fill_suggestions = self.generate_fill_suggestions(text, job_data, photos)
        
        # Annotate PDF with red/blue markings
        annotated_pdf = self.annotate_pdf(pdf_content, fill_suggestions)
        
        # Generate certification sheet if needed
        cert_sheet = self.generate_cert_sheet(job_data)
        
        # Generate pole report
        pole_report = self.pole_classifier.generate_pole_report(
            pole_type, pole_confidence, 
            {'levels': 0, 'equipment': []},  # Would be extracted from features
            pricing
        )
        
        # Validate submittal completeness
        validation = self.doc_ordering.validate_submittal(ordered_docs, work_type, pole_type)
        
        return {
            'annotated_pdf': annotated_pdf,
            'work_type': work_type,
            'pole_type': pole_type,
            'pole_confidence': pole_confidence * 100,
            'pole_reason': pole_reason,
            'pole_report': pole_report,
            'ordered_documents': ordered_docs,
            'document_validation': validation,
            'mat_codes': mat_codes,
            'pricing': pricing,
            'fill_suggestions': fill_suggestions,
            'cert_sheet': cert_sheet,
            'compliance_score': validation['completeness']
        }
    
    def extract_pdf_text(self, pdf_content: bytes) -> str:
        """Extract text from PDF bytes"""
        try:
            pdf_reader = PyPDF2.PdfReader(io.BytesIO(pdf_content))
            text = ""
            for page in pdf_reader.pages:
                text += page.extract_text()
            return text
        except Exception as e:
            logger.error(f"Error extracting PDF text: {e}")
            return ""
    
    def extract_mat_codes(self, text: str) -> List[Dict]:
        """Extract material codes from text"""
        mat_codes = []
        
        # Pattern for material codes (adjust based on actual format)
        patterns = [
            r'Mat[.\s]*([A-Z0-9]+)',  # Mat Z, Mat A123
            r'Material[:\s]*([A-Z0-9]+)',
            r'Code[:\s]*([A-Z0-9]+)',
            r'([A-Z]\d{3,6})',  # Letter followed by 3-6 digits
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                mat_codes.append({
                    'code': match,
                    'quantity': 1,  # Would need to extract quantity too
                    'description': self.get_mat_description(match)
                })
        
        # Remove duplicates
        seen = set()
        unique = []
        for item in mat_codes:
            if item['code'] not in seen:
                seen.add(item['code'])
                unique.append(item)
        
        return unique
    
    def get_mat_description(self, code: str) -> str:
        """Get material description from code"""
        # This would lookup from materials database
        descriptions = {
            'Z': 'Pole Hardware Kit',
            'A': 'Transformer 25kVA',
            'B': 'Cross-arm Assembly',
            # Add more from actual materials list
        }
        return descriptions.get(code, f'Material {code}')
    
    def load_mat_prices(self) -> Dict[str, float]:
        """Load material prices from storage"""
        try:
            with open(f'{self.data_path}/mat_prices.json', 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            # Default prices for demo
            return {
                'Z': 200.00,
                'A': 500.00,
                'B': 350.00,
                'C': 150.00,
                # Add more defaults
            }
    
    def calculate_pricing(self, mat_codes: List[Dict]) -> Dict:
        """Calculate total pricing from material codes"""
        total = 0
        breakdown = []
        
        for item in mat_codes:
            code = item['code']
            qty = item.get('quantity', 1)
            price = self.mat_prices.get(code, 0)
            line_total = price * qty
            total += line_total
            
            breakdown.append({
                'code': code,
                'description': item.get('description', ''),
                'quantity': qty,
                'unit_price': price,
                'total': line_total
            })
        
        return {
            'total': total,
            'breakdown': breakdown,
            'currency': 'USD'
        }
    
    def generate_fill_suggestions(self, text: str, job_data: Dict, 
                                 photos: Optional[List[str]] = None) -> Dict:
        """Generate intelligent fill suggestions based on rules"""
        suggestions = {
            'red_line': [],
            'blue_line': [],
            'changes': [],
            'notes': []
        }
        
        # Extract PM and Notification numbers
        pm_number = job_data.get('pm_number', '')
        notification = job_data.get('notification_number', '')
        
        # Check for "not installed" items
        not_installed_pattern = r'not\s+installed|removed|deleted|omitted'
        if re.search(not_installed_pattern, text, re.IGNORECASE):
            suggestions['red_line'].append({
                'action': 'strike_through',
                'reason': 'Items marked as not installed',
                'instruction': 'Use red pen to strike through'
            })
        
        # Check for changes
        change_pattern = r'changed?\s+to|modified|replaced|substituted'
        changes = re.findall(change_pattern, text, re.IGNORECASE)
        if changes:
            suggestions['red_line'].append({
                'action': 'write_change',
                'items': changes,
                'instruction': 'Write specific changes in red'
            })
        
        # Check for field findings
        if 'FIF' in text or 'found in field' in text.lower():
            suggestions['blue_line'].append({
                'action': 'add_note',
                'type': 'FIF',
                'instruction': 'Document Found In Field items in blue'
            })
        
        # Check for FCOA
        if 'FCOA' in text or 'field change' in text.lower():
            suggestions['blue_line'].append({
                'action': 'add_note',
                'type': 'FCOA',
                'instruction': 'Add Field Change Order Authorization in blue'
            })
        
        # Add photo references if provided
        if photos:
            suggestions['notes'].append({
                'type': 'photos',
                'count': len(photos),
                'instruction': f'Reference {len(photos)} field photos attached'
            })
        
        return suggestions
    
    def annotate_pdf(self, pdf_content: bytes, suggestions: Dict) -> bytes:
        """
        Annotate PDF with red/blue markings based on suggestions
        Returns annotated PDF bytes
        """
        try:
            # Create overlay with annotations
            packet = io.BytesIO()
            can = canvas.Canvas(packet, pagesize=letter)
            
            # Add red line annotations
            y_position = 750
            for red_item in suggestions.get('red_line', []):
                can.setFillColorRGB(1, 0, 0)  # Red
                can.setFont("Helvetica", 10)
                
                if red_item['action'] == 'strike_through':
                    can.drawString(30, y_position, f"⚠ {red_item['instruction']}")
                    y_position -= 20
                elif red_item['action'] == 'write_change':
                    can.drawString(30, y_position, f"✏ {red_item['instruction']}")
                    y_position -= 20
            
            # Add blue line annotations
            for blue_item in suggestions.get('blue_line', []):
                can.setFillColorRGB(0, 0, 1)  # Blue
                can.setFont("Helvetica", 10)
                can.drawString(30, y_position, f"📝 {blue_item['instruction']}")
                y_position -= 20
            
            # Add compliance stamp
            can.setFillColorRGB(0, 0.5, 0)  # Green
            can.setFont("Helvetica-Bold", 12)
            can.drawString(400, 750, "PG&E COMPLIANT")
            
            can.save()
            
            # Merge with original PDF
            packet.seek(0)
            overlay_pdf = PyPDF2.PdfReader(packet)
            original_pdf = PyPDF2.PdfReader(io.BytesIO(pdf_content))
            output = PyPDF2.PdfWriter()
            
            # Add overlay to first page
            if len(original_pdf.pages) > 0:
                page = original_pdf.pages[0]
                if len(overlay_pdf.pages) > 0:
                    page.merge_page(overlay_pdf.pages[0])
                output.add_page(page)
                
                # Add remaining pages
                for i in range(1, len(original_pdf.pages)):
                    output.add_page(original_pdf.pages[i])
            
            # Write to bytes
            output_stream = io.BytesIO()
            output.write(output_stream)
            return output_stream.getvalue()
            
        except Exception as e:
            logger.error(f"Error annotating PDF: {e}")
            return pdf_content  # Return original if annotation fails
    
    def generate_cert_sheet(self, job_data: Dict) -> Dict:
        """Generate Field Verification Certification Sheet"""
        pm_number = job_data.get('pm_number', 'N/A')
        notification = job_data.get('notification_number', 'N/A')
        
        cert = {
            'title': 'Field Verification Certification Sheet',
            'job_number': f"PM: {pm_number} / Notification: {notification}",
            'built_as_designed': None,  # To be filled
            'changes': [],
            'lan_id': None,  # To be filled
            'date': None,  # To be filled
            'signature': None,  # To be filled
            'template': self.generate_cert_template(pm_number, notification)
        }
        
        return cert
    
    def generate_cert_template(self, pm_number: str, notification: str) -> str:
        """Generate certification sheet template"""
        template = f"""
        FIELD VERIFICATION CERTIFICATION SHEET
        =====================================
        
        Job Number: PM {pm_number} / Notification {notification}
        
        [ ] Built As Designed
        [ ] Built with Changes (explain below)
        
        Changes/Modifications:
        _________________________________
        _________________________________
        _________________________________
        
        Field Verification By:
        LAN ID: _______________
        Date: _________________
        Signature: ____________
        
        Reviewed By:
        LAN ID: _______________
        Date: _________________
        Signature: ____________
        
        =====================================
        Per PG&E As-Built Procedure 2025
        """
        return template
    
    def calculate_compliance(self, text: str, required_docs: List[str]) -> float:
        """Calculate compliance score based on document completeness"""
        found_docs = 0
        for doc in required_docs:
            if doc.lower() in text.lower():
                found_docs += 1
        
        score = (found_docs / len(required_docs)) * 100 if required_docs else 0
        return round(score, 2)
    
    def update_mat_prices(self, prices_data: Dict) -> bool:
        """Update material prices in persistent storage"""
        try:
            # Merge with existing prices
            current_prices = self.load_mat_prices()
            current_prices.update(prices_data)
            
            # Save to storage
            with open(f'{self.data_path}/mat_prices.json', 'w') as f:
                json.dump(current_prices, f, indent=2)
            
            # Reload prices
            self.mat_prices = current_prices
            logger.info(f"Updated {len(prices_data)} material prices")
            return True
            
        except Exception as e:
            logger.error(f"Error updating material prices: {e}")
            return False
