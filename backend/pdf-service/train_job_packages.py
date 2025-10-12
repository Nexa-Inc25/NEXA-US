"""
Train NEXA on Job Packages and As-Builts
This is CRITICAL - NEXA needs to learn the structure of job packages
and how to fill them out to PG&E standards!
"""

import os
import json
import logging
from typing import List, Dict, Any
from sentence_transformers import SentenceTransformer
import PyPDF2
import pickle
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class JobPackageTrainer:
    """
    Train NEXA on real job packages and as-builts
    so it knows how to fill them the fuck out!
    """
    
    def __init__(self, data_dir: str = "/data"):
        self.data_dir = data_dir
        self.model = SentenceTransformer('all-MiniLM-L6-v2')
        self.job_package_patterns = {}
        self.field_mappings = {}
        self.as_built_templates = {}
        
    def learn_job_package_structure(self, pdf_path: str) -> Dict[str, Any]:
        """
        Learn the structure of a job package - what fields exist,
        where they are, what format they need
        """
        logger.info(f"🎯 Learning job package structure from: {pdf_path}")
        
        # Extract all fields from the PDF
        fields = self.extract_pdf_fields(pdf_path)
        
        # Learn the patterns
        package_structure = {
            "file_name": os.path.basename(pdf_path),
            "learned_at": datetime.now().isoformat(),
            "fields": {},
            "sections": {},
            "required_documents": []
        }
        
        # Identify key fields NEXA needs to fill
        key_fields = [
            # Job Information
            "PM_NUMBER",
            "NOTIFICATION_NUMBER", 
            "JOB_NAME",
            "LOCATION",
            "DISTRICT",
            "DIVISION",
            
            # Work Details
            "WORK_TYPE",  # Pole replacement, crossarm, etc
            "POLE_NUMBER",
            "POLE_TYPE",
            "POLE_HEIGHT",
            "CROSSARM_TYPE",
            
            # Dates
            "START_DATE",
            "COMPLETION_DATE",
            "INSPECTION_DATE",
            
            # Crew Information
            "FOREMAN_NAME",
            "CREW_NUMBER",
            "CONTRACTOR",
            
            # Materials Used
            "MATERIALS_LIST",
            "EQUIPMENT_USED",
            
            # Compliance
            "PERMIT_NUMBER",
            "SPEC_REFERENCE",  # Which PG&E spec applies
            "COMPLIANCE_NOTES",
            
            # As-Built Specifics
            "AS_BUILT_DRAWING",
            "GPS_COORDINATES",
            "BEFORE_PHOTO",
            "AFTER_PHOTO",
            
            # QA Section
            "QA_INSPECTOR",
            "QA_DATE",
            "QA_NOTES",
            "INFRACTIONS_FOUND",
            "REMEDIATION_COMPLETE"
        ]
        
        # Extract and learn each field
        for field_name in key_fields:
            field_data = self.find_field_in_pdf(fields, field_name)
            if field_data:
                package_structure["fields"][field_name] = {
                    "location": field_data.get("page", 1),
                    "format": field_data.get("format", "text"),
                    "required": field_data.get("required", True),
                    "example": field_data.get("value", ""),
                    "validation": self.learn_field_validation(field_name)
                }
                logger.info(f"  ✅ Learned field: {field_name}")
        
        # Save the learned structure
        self.save_package_structure(package_structure)
        
        return package_structure
    
    def learn_as_built_format(self, as_built_pdf: str) -> Dict[str, Any]:
        """
        Learn how to fill out as-builts from completed examples
        """
        logger.info(f"📝 Learning as-built format from: {as_built_pdf}")
        
        # Extract the filled as-built
        filled_data = self.extract_pdf_fields(as_built_pdf)
        
        # Learn the filling patterns
        as_built_pattern = {
            "template_name": os.path.basename(as_built_pdf),
            "learned_at": datetime.now().isoformat(),
            "filling_rules": {},
            "auto_fill_mappings": {}
        }
        
        # Learn how fields are filled
        for field_name, field_value in filled_data.items():
            # Learn the pattern
            pattern = {
                "field_name": field_name,
                "value_format": self.analyze_value_format(field_value),
                "source": self.identify_data_source(field_name),
                "transformation": self.learn_transformation_rule(field_name, field_value)
            }
            as_built_pattern["filling_rules"][field_name] = pattern
            
            # Map to auto-fill source
            if pattern["source"]:
                as_built_pattern["auto_fill_mappings"][field_name] = pattern["source"]
        
        # Save the learned pattern
        self.save_as_built_pattern(as_built_pattern)
        
        return as_built_pattern
    
    def extract_pdf_fields(self, pdf_path: str) -> Dict[str, Any]:
        """
        Extract all fields and their values from a PDF
        """
        fields = {}
        
        try:
            with open(pdf_path, 'rb') as file:
                reader = PyPDF2.PdfReader(file)
                
                # Get form fields if it's a fillable PDF
                if reader.get_form_text_fields():
                    fields = reader.get_form_text_fields()
                
                # Also extract text to find field patterns
                for page_num, page in enumerate(reader.pages):
                    text = page.extract_text()
                    # Parse text for field:value patterns
                    lines = text.split('\n')
                    for line in lines:
                        if ':' in line:
                            parts = line.split(':', 1)
                            if len(parts) == 2:
                                field_key = parts[0].strip().upper().replace(' ', '_')
                                field_value = parts[1].strip()
                                if field_key and field_value:
                                    fields[field_key] = {
                                        'value': field_value,
                                        'page': page_num + 1,
                                        'format': self.detect_format(field_value)
                                    }
        except Exception as e:
            logger.error(f"Error extracting PDF fields: {e}")
        
        return fields
    
    def find_field_in_pdf(self, fields: Dict, field_name: str) -> Dict:
        """
        Find a specific field in extracted PDF data
        """
        # Direct match
        if field_name in fields:
            return fields[field_name]
        
        # Fuzzy match
        for key, value in fields.items():
            if field_name.lower() in key.lower() or key.lower() in field_name.lower():
                return value
        
        return {}
    
    def learn_field_validation(self, field_name: str) -> Dict[str, Any]:
        """
        Learn validation rules for each field based on PG&E requirements
        """
        validations = {
            "PM_NUMBER": {
                "pattern": r"PM-\d{4}-\d{3}",
                "required": True,
                "error_message": "PM Number must be format PM-YYYY-XXX"
            },
            "NOTIFICATION_NUMBER": {
                "pattern": r"\d{10}",
                "required": False,
                "error_message": "Notification must be 10 digits"
            },
            "POLE_TYPE": {
                "options": ["Wood", "Steel", "Concrete", "Composite"],
                "required": True,
                "error_message": "Must select valid pole type"
            },
            "POLE_HEIGHT": {
                "min": 20,
                "max": 120,
                "unit": "feet",
                "required": True,
                "error_message": "Pole height must be 20-120 feet"
            },
            "GPS_COORDINATES": {
                "pattern": r"[-]?\d+\.\d+,\s*[-]?\d+\.\d+",
                "required": True,
                "error_message": "GPS must be lat,lon format"
            }
        }
        
        return validations.get(field_name, {"required": False})
    
    def analyze_value_format(self, value: Any) -> str:
        """
        Determine the format of a field value
        """
        if isinstance(value, dict):
            return "object"
        elif isinstance(value, (list, tuple)):
            return "array"
        elif isinstance(value, bool):
            return "boolean"
        elif isinstance(value, (int, float)):
            return "number"
        elif isinstance(value, str):
            # Check for specific formats
            if value.isdigit():
                return "number_string"
            elif '/' in value or '-' in value:
                return "date"
            elif '@' in value:
                return "email"
            elif value.upper() in ['YES', 'NO', 'Y', 'N']:
                return "boolean_string"
            else:
                return "text"
        return "unknown"
    
    def identify_data_source(self, field_name: str) -> str:
        """
        Identify where the data for this field comes from
        """
        source_mappings = {
            # From job upload
            "PM_NUMBER": "job_package.pm_number",
            "NOTIFICATION_NUMBER": "job_package.notification_number",
            "JOB_NAME": "job_package.job_name",
            
            # From pre-field
            "FOREMAN_NAME": "prefield.foreman_assigned",
            "CREW_NUMBER": "prefield.crew_id",
            "START_DATE": "prefield.scheduled_date",
            
            # From field completion
            "COMPLETION_DATE": "completion.date",
            "BEFORE_PHOTO": "completion.photos.before",
            "AFTER_PHOTO": "completion.photos.after",
            "GPS_COORDINATES": "completion.gps",
            "MATERIALS_LIST": "completion.materials_used",
            
            # From NEXA analysis
            "INFRACTIONS_FOUND": "nexa.infraction_check",
            "SPEC_REFERENCE": "nexa.spec_lookup",
            "COMPLIANCE_NOTES": "nexa.compliance_analysis",
            
            # From QA
            "QA_INSPECTOR": "qa.inspector_name",
            "QA_DATE": "qa.review_date",
            "QA_NOTES": "qa.notes"
        }
        
        return source_mappings.get(field_name, "manual_entry")
    
    def learn_transformation_rule(self, field_name: str, field_value: str) -> str:
        """
        Learn how to transform raw data into the required field format
        """
        # Examples of transformation rules
        if field_name == "COMPLETION_DATE" and "/" in field_value:
            return "format_date('MM/DD/YYYY')"
        elif field_name == "GPS_COORDINATES":
            return "format_gps('decimal_degrees')"
        elif field_name == "MATERIALS_LIST":
            return "format_list('comma_separated')"
        elif field_name.endswith("_PHOTO"):
            return "attach_file('image/jpeg')"
        else:
            return "copy_value()"
    
    def detect_format(self, value: str) -> str:
        """
        Detect the format of a value
        """
        if not value:
            return "empty"
        elif value.isdigit():
            return "number"
        elif '/' in value or '-' in value and any(c.isdigit() for c in value):
            return "date"
        elif '@' in value:
            return "email"
        elif value.upper() in ['YES', 'NO', 'TRUE', 'FALSE']:
            return "boolean"
        else:
            return "text"
    
    def save_package_structure(self, structure: Dict):
        """
        Save learned package structure
        """
        file_path = os.path.join(self.data_dir, "job_package_structures.json")
        
        # Load existing structures
        existing = {}
        if os.path.exists(file_path):
            with open(file_path, 'r') as f:
                existing = json.load(f)
        
        # Add new structure
        package_type = structure.get("file_name", "unknown")
        existing[package_type] = structure
        
        # Save updated structures
        with open(file_path, 'w') as f:
            json.dump(existing, f, indent=2)
        
        logger.info(f"✅ Saved package structure to {file_path}")
    
    def save_as_built_pattern(self, pattern: Dict):
        """
        Save learned as-built pattern
        """
        file_path = os.path.join(self.data_dir, "as_built_patterns.json")
        
        # Load existing patterns
        existing = {}
        if os.path.exists(file_path):
            with open(file_path, 'r') as f:
                existing = json.load(f)
        
        # Add new pattern
        template_name = pattern.get("template_name", "unknown")
        existing[template_name] = pattern
        
        # Save updated patterns
        with open(file_path, 'w') as f:
            json.dump(existing, f, indent=2)
        
        logger.info(f"✅ Saved as-built pattern to {file_path}")

def train_on_job_packages():
    """
    Main training function - upload your job packages here!
    """
    trainer = JobPackageTrainer()
    
    # Train on job packages
    job_packages = [
        "sample_job_package_1.pdf",
        "sample_job_package_2.pdf",
        # Add your actual job packages here!
    ]
    
    for package_pdf in job_packages:
        if os.path.exists(package_pdf):
            logger.info(f"\n🎯 Training on: {package_pdf}")
            structure = trainer.learn_job_package_structure(package_pdf)
            logger.info(f"  Learned {len(structure['fields'])} fields")
    
    # Train on completed as-builts
    as_builts = [
        "completed_as_built_1.pdf",
        "completed_as_built_2.pdf",
        # Add your actual completed as-builts here!
    ]
    
    for as_built_pdf in as_builts:
        if os.path.exists(as_built_pdf):
            logger.info(f"\n📝 Training on as-built: {as_built_pdf}")
            pattern = trainer.learn_as_built_format(as_built_pdf)
            logger.info(f"  Learned {len(pattern['filling_rules'])} filling rules")
    
    logger.info("\n✅ Training complete! NEXA now knows how to fill out job packages!")

if __name__ == "__main__":
    train_on_job_packages()
