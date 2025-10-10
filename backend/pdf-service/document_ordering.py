"""
PG&E As-Built Document Ordering System
Orders submittal documents according to PG&E standards
"""
import re
import json
from typing import List, Dict, Optional, Tuple
import logging

logger = logging.getLogger(__name__)

class DocumentOrderingSystem:
    """Order as-built documents per PG&E submittal requirements"""
    
    def __init__(self, data_path: str = '/data'):
        self.data_path = data_path
        self.standard_order = self.load_standard_order()
        self.work_type_requirements = self.load_work_type_requirements()
        
    def load_standard_order(self) -> List[str]:
        """Load standard document order from PG&E spec"""
        # This order is from "As-Built document order (1).pdf"
        return [
            'POLE BILL',
            'EC TAG',
            'CONSTRUCTION DRAWING',
            'KEY SKETCH',
            'WRG FORM',
            'CREW INSTRUCTIONS',
            'CREW MATERIALS LIST',
            'CFSS',
            'POLE EQUIPMENT FORM',
            'CMCS',
            'FORM 23',
            'FORM 48',
            'FAS SCREEN CAPTURE',
            'FIELD VERIFICATION CERTIFICATION SHEET',
            'PHOTOS',
            'FDA ATTACHMENTS',
            'SWITCHING SUMMARY',
            'UNIT COMPLETION REPORT',
            'SAFETY DOCUMENTATION',
            'CCSC'  # Last per spec
        ]
    
    def load_work_type_requirements(self) -> Dict[str, List[str]]:
        """Load document requirements by work type"""
        # Enhanced from Table 3 with pole type considerations
        return {
            'Planned Estimated': [
                'EC TAG', 'CONSTRUCTION DRAWING', 'KEY SKETCH',
                'CREW INSTRUCTIONS', 'CREW MATERIALS LIST', 'CFSS',
                'POLE EQUIPMENT FORM', 'CMCS', 'FORM 23', 'FORM 48',
                'FAS SCREEN CAPTURE'
            ],
            'Routine Emergency Estimated': [
                'EC TAG', 'CONSTRUCTION DRAWING', 'CREW INSTRUCTIONS',
                'CREW MATERIALS LIST', 'CFSS', 'POLE EQUIPMENT FORM',
                'CMCS', 'FORM 23', 'FORM 48'
            ],
            'Planned WRG': [
                'CONSTRUCTION DRAWING', 'KEY SKETCH', 'WRG FORM',
                'CREW INSTRUCTIONS', 'CREW MATERIALS LIST', 'CFSS',
                'POLE EQUIPMENT FORM', 'CMCS', 'FORM 23', 'FORM 48'
            ],
            'Emergency Unit Completion': [
                'UNIT COMPLETION REPORT', 'SWITCHING SUMMARY',
                'SAFETY DOCUMENTATION', 'PHOTOS'
            ],
            'Routine Maintenance': [
                'EC TAG', 'CREW INSTRUCTIONS', 'CREW MATERIALS LIST',
                'FORM 23', 'PHOTOS'
            ]
        }
    
    def extract_document_order(self, pdf_text: str) -> List[str]:
        """Extract document order from uploaded PG&E spec PDF"""
        order = []
        
        # Look for bullet points or numbered lists
        patterns = [
            r'[•·\-]\s*(.+)',  # Bullet points
            r'\d+\.\s*(.+)',   # Numbered list
            r'^\s*([A-Z\s]+(?:FORM|TAG|SHEET|REPORT|DRAWING))',  # Document names
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, pdf_text, re.MULTILINE)
            if matches:
                order.extend([m.strip().upper() for m in matches])
        
        # Remove duplicates while preserving order
        seen = set()
        unique_order = []
        for doc in order:
            if doc not in seen and len(doc) > 3:  # Skip short matches
                seen.add(doc)
                unique_order.append(doc)
        
        # Save to persistent storage
        if unique_order:
            try:
                with open(f'{self.data_path}/document_order.json', 'w') as f:
                    json.dump(unique_order, f, indent=2)
                logger.info(f"Extracted and saved document order: {len(unique_order)} documents")
            except Exception as e:
                logger.error(f"Error saving document order: {e}")
        
        return unique_order if unique_order else self.standard_order
    
    def get_required_documents(self, work_type: str, pole_type: int) -> List[str]:
        """Get required documents based on work type and pole type"""
        # Start with base requirements for work type
        base_docs = self.work_type_requirements.get(work_type, [])
        
        # Add pole-type specific documents
        pole_specific = []
        
        if pole_type >= 3:  # Type 3+ requires additional documentation
            pole_specific.extend([
                'POLE EQUIPMENT FORM',
                'FIELD VERIFICATION CERTIFICATION SHEET'
            ])
        
        if pole_type >= 4:  # Type 4+ requires photos
            pole_specific.append('PHOTOS')
        
        if pole_type == 5:  # Type 5 requires special documentation
            pole_specific.extend([
                'FDA ATTACHMENTS',
                'SPECIAL EQUIPMENT DOCUMENTATION',
                'BID/NTE JUSTIFICATION'
            ])
        
        # Combine and deduplicate
        all_docs = list(set(base_docs + pole_specific))
        
        return all_docs
    
    def sort_documents(self, documents: List[str], 
                      work_type: Optional[str] = None,
                      pole_type: Optional[int] = None) -> List[str]:
        """
        Sort documents according to PG&E standard order
        
        Args:
            documents: List of document names to sort
            work_type: Optional work type for filtering
            pole_type: Optional pole type for additional requirements
            
        Returns:
            Sorted list of documents
        """
        # Normalize document names
        normalized_docs = [self.normalize_doc_name(doc) for doc in documents]
        
        # Get required documents if work type specified
        if work_type:
            required = self.get_required_documents(work_type, pole_type or 3)
            # Add any missing required documents
            for req_doc in required:
                if req_doc not in normalized_docs:
                    normalized_docs.append(req_doc)
                    logger.info(f"Added required document: {req_doc}")
        
        # Sort according to standard order
        sorted_docs = []
        
        # First add documents in standard order
        for standard_doc in self.standard_order:
            matching_docs = [doc for doc in normalized_docs 
                           if self.match_document(doc, standard_doc)]
            sorted_docs.extend(matching_docs)
        
        # Then add any documents not in standard order
        for doc in normalized_docs:
            if doc not in sorted_docs:
                sorted_docs.append(doc)
                logger.warning(f"Document not in standard order: {doc}")
        
        return sorted_docs
    
    def normalize_doc_name(self, doc_name: str) -> str:
        """Normalize document name for matching"""
        # Remove special characters and standardize
        normalized = doc_name.upper()
        normalized = re.sub(r'[^\w\s]', ' ', normalized)
        normalized = ' '.join(normalized.split())
        
        # Common abbreviations
        replacements = {
            'XFMR': 'TRANSFORMER',
            'EQUIP': 'EQUIPMENT',
            'CERT': 'CERTIFICATION',
            'DOC': 'DOCUMENT',
            'INSTR': 'INSTRUCTIONS'
        }
        
        for abbr, full in replacements.items():
            normalized = normalized.replace(abbr, full)
        
        return normalized
    
    def match_document(self, doc: str, standard: str) -> bool:
        """Check if a document matches a standard name"""
        # Direct match
        if doc == standard:
            return True
        
        # Partial match (all words from standard are in doc)
        standard_words = set(standard.split())
        doc_words = set(doc.split())
        
        if standard_words.issubset(doc_words):
            return True
        
        # Key term match
        key_terms = ['POLE BILL', 'EC TAG', 'WRG', 'CMCS', 'CFSS', 'FDA']
        for term in key_terms:
            if term in standard and term in doc:
                return True
        
        return False
    
    def validate_submittal(self, documents: List[str], 
                          work_type: str,
                          pole_type: int) -> Dict:
        """
        Validate if submittal has all required documents
        
        Returns:
            Dict with validation results
        """
        required = self.get_required_documents(work_type, pole_type)
        provided = [self.normalize_doc_name(doc) for doc in documents]
        
        missing = []
        for req_doc in required:
            if not any(self.match_document(prov, req_doc) for prov in provided):
                missing.append(req_doc)
        
        extra = []
        for prov in provided:
            if not any(self.match_document(prov, req) for req in required):
                extra.append(prov)
        
        completeness = (len(required) - len(missing)) / len(required) * 100 if required else 100
        
        return {
            'valid': len(missing) == 0,
            'completeness': round(completeness, 1),
            'required_count': len(required),
            'provided_count': len(provided),
            'missing_documents': missing,
            'extra_documents': extra,
            'work_type': work_type,
            'pole_type': pole_type
        }
    
    def generate_submittal_checklist(self, work_type: str, pole_type: int) -> str:
        """Generate a submittal checklist for the given work type and pole type"""
        required = self.get_required_documents(work_type, pole_type)
        sorted_docs = self.sort_documents(required, work_type, pole_type)
        
        checklist = f"PG&E AS-BUILT SUBMITTAL CHECKLIST\n"
        checklist += f"{'=' * 40}\n"
        checklist += f"Work Type: {work_type}\n"
        checklist += f"Pole Type: {pole_type}\n"
        checklist += f"{'=' * 40}\n\n"
        checklist += "Required Documents (in order):\n"
        
        for i, doc in enumerate(sorted_docs, 1):
            checklist += f"  {i:2d}. [ ] {doc}\n"
        
        checklist += f"\n{'=' * 40}\n"
        checklist += f"Total Documents Required: {len(sorted_docs)}\n"
        
        if pole_type == 5:
            checklist += "\n⚠️ NOTE: Type 5 pole requires Bid/NTE documentation\n"
        
        return checklist
    
    def create_submittal_package(self, documents: Dict[str, bytes],
                                work_type: str,
                                pole_type: int) -> Tuple[List[str], Dict]:
        """
        Create ordered submittal package
        
        Args:
            documents: Dict mapping document names to their content (bytes)
            work_type: Work type for the submittal
            pole_type: Pole type classification
            
        Returns:
            Tuple of (ordered_document_list, validation_results)
        """
        # Sort documents
        doc_names = list(documents.keys())
        sorted_names = self.sort_documents(doc_names, work_type, pole_type)
        
        # Validate completeness
        validation = self.validate_submittal(doc_names, work_type, pole_type)
        
        # Add checklist to package
        checklist = self.generate_submittal_checklist(work_type, pole_type)
        
        package = {
            'ordered_documents': sorted_names,
            'validation': validation,
            'checklist': checklist,
            'work_type': work_type,
            'pole_type': pole_type,
            'document_count': len(sorted_names)
        }
        
        logger.info(f"Created submittal package: {len(sorted_names)} documents, "
                   f"{validation['completeness']}% complete")
        
        return sorted_names, package
