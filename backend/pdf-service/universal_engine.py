"""
NEXA Universal Standards Engine
Core engine for standardizing all utility specs and intelligently applying them
"""
import os
import json
import hashlib
import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from uuid import UUID, uuid4
import asyncpg
import numpy as np
from sentence_transformers import SentenceTransformer
import PyPDF2
import re
from pydantic import BaseModel

logger = logging.getLogger(__name__)

# Configuration
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:password@localhost/nexa")
DATA_PATH = os.getenv("DATA_PATH", "/data")

# Universal standard categories
UNIVERSAL_CATEGORIES = {
    "CLEARANCE": ["pole_clearance", "line_clearance", "vegetation_clearance"],
    "GROUNDING": ["pole_grounding", "equipment_grounding", "guy_grounding"],
    "EQUIPMENT": ["transformers", "capacitors", "switches", "reclosers"],
    "STRUCTURAL": ["poles", "crossarms", "guys", "anchors"],
    "SAFETY": ["climbing_space", "working_space", "public_safety"]
}

class UniversalEngine:
    """Main engine for universal standards processing"""
    
    def __init__(self):
        self.db_pool = None
        self.embedder = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')
        self.utility_cache = {}
        logger.info("Universal Standards Engine initialized")
    
    async def initialize(self):
        """Initialize database connection and cache"""
        self.db_pool = await asyncpg.create_pool(DATABASE_URL)
        await self._load_utilities()
        logger.info(f"Loaded {len(self.utility_cache)} utilities")
    
    async def _load_utilities(self):
        """Load utility configurations into cache"""
        query = "SELECT * FROM utilities_master"
        async with self.db_pool.acquire() as conn:
            utilities = await conn.fetch(query)
            for u in utilities:
                self.utility_cache[u['code']] = {
                    'id': u['id'],
                    'name': u['name'],
                    'region': json.loads(u['region']) if u['region'] else {},
                    'patterns': json.loads(u['form_patterns']) if u['form_patterns'] else {},
                    'spec_patterns': json.loads(u['spec_patterns']) if u['spec_patterns'] else {},
                    'nomenclature': json.loads(u['nomenclature']) if u['nomenclature'] else {}
                }
    
    async def ingest_spec(self, utility_code: str, pdf_content: bytes, 
                         filename: str) -> Dict:
        """Ingest and standardize a utility spec document"""
        
        logger.info(f"Ingesting spec for {utility_code}: {filename}")
        
        utility = self.utility_cache.get(utility_code)
        if not utility:
            raise ValueError(f"Unknown utility: {utility_code}")
        
        # Extract text from PDF
        text = self._extract_pdf_text(pdf_content)
        
        # Parse into sections based on utility patterns
        sections = self._parse_sections(text, utility['spec_patterns'])
        
        # Standardize and store each section
        standardized_count = 0
        for section in sections:
            # Classify into universal category
            category = self._classify_text(section['text'])
            
            # Standardize terminology
            std_text = self._standardize_terminology(
                section['text'], 
                utility['nomenclature']
            )
            
            # Extract structured values
            values = self._extract_values(std_text)
            
            # Generate embedding
            embedding = self.embedder.encode(std_text).tolist()
            
            # Store in data lake
            query = """
                INSERT INTO standards_data_lake (
                    utility_id, standard_category, standard_subcategory,
                    standard_code, utility_reference, requirement_text,
                    requirement_value, embedding
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            """
            
            async with self.db_pool.acquire() as conn:
                await conn.execute(
                    query,
                    utility['id'],
                    category['category'],
                    category['subcategory'],
                    self._generate_code(category),
                    section.get('reference', ''),
                    std_text,
                    json.dumps(values),
                    embedding
                )
            
            standardized_count += 1
        
        logger.info(f"Standardized {standardized_count} requirements from {filename}")
        
        return {
            "utility": utility_code,
            "filename": filename,
            "sections_found": len(sections),
            "requirements_standardized": standardized_count,
            "status": "success"
        }
    
    def _extract_pdf_text(self, pdf_content: bytes) -> str:
        """Extract text from PDF content"""
        import io
        pdf_file = io.BytesIO(pdf_content)
        pdf_reader = PyPDF2.PdfReader(pdf_file)
        
        text = ""
        for page_num in range(len(pdf_reader.pages)):
            page = pdf_reader.pages[page_num]
            text += page.extract_text() + "\n"
        
        return text
    
    def _parse_sections(self, text: str, patterns: Dict) -> List[Dict]:
        """Parse text into sections based on utility patterns"""
        sections = []
        
        # Default section pattern if none provided
        section_pattern = patterns.get('section', r'Section \d+')
        
        # Split by section markers
        parts = re.split(f'({section_pattern})', text)
        
        for i in range(1, len(parts), 2):
            if i + 1 < len(parts):
                sections.append({
                    'reference': parts[i].strip(),
                    'text': parts[i + 1].strip()[:2000]  # Limit length
                })
        
        return sections
    
    def _classify_text(self, text: str) -> Dict:
        """Classify text into universal category"""
        text_lower = text.lower()
        
        for category, subcategories in UNIVERSAL_CATEGORIES.items():
            for subcat in subcategories:
                keywords = subcat.replace('_', ' ').split()
                if all(kw in text_lower for kw in keywords):
                    return {
                        "category": category,
                        "subcategory": subcat
                    }
        
        return {
            "category": "GENERAL",
            "subcategory": "other"
        }
    
    def _standardize_terminology(self, text: str, nomenclature: Dict) -> str:
        """Replace utility-specific terms with universal ones"""
        standardized = text
        
        for universal_term, variations in nomenclature.items():
            for variation in variations:
                # Case-insensitive replacement
                pattern = re.compile(re.escape(variation), re.IGNORECASE)
                standardized = pattern.sub(universal_term, standardized)
        
        return standardized
    
    def _extract_values(self, text: str) -> Dict:
        """Extract numerical values and units from text"""
        values = {}
        
        # Extract distances/clearances
        distance_pattern = r'(\d+(?:\.\d+)?)\s*(feet|ft|inches|in|meters|m)'
        distances = re.findall(distance_pattern, text, re.IGNORECASE)
        if distances:
            values['distances'] = [
                {"value": float(d[0]), "unit": d[1]} for d in distances
            ]
        
        # Extract voltages
        voltage_pattern = r'(\d+(?:\.\d+)?)\s*(kV|V|kilovolts|volts)'
        voltages = re.findall(voltage_pattern, text, re.IGNORECASE)
        if voltages:
            values['voltages'] = [
                {"value": float(v[0]), "unit": v[1]} for v in voltages
            ]
        
        # Extract percentages
        percent_pattern = r'(\d+(?:\.\d+)?)\s*%'
        percentages = re.findall(percent_pattern, text)
        if percentages:
            values['percentages'] = [float(p) for p in percentages]
        
        return values
    
    def _generate_code(self, category: Dict) -> str:
        """Generate universal standard code"""
        prefix = category['category'][:2].upper()
        suffix = hashlib.md5(
            f"{category['subcategory']}{datetime.now()}".encode()
        ).hexdigest()[:6].upper()
        return f"{prefix}-{suffix}"
    
    async def detect_utility_for_job(self, lat: float, lng: float, 
                                   address: str = None) -> str:
        """Detect which utility serves a location"""
        
        # Simplified utility detection based on coordinates
        # In production, use actual GIS boundaries
        
        if lat > 36 and lat < 42 and lng > -124 and lng < -120:
            return "PGE"  # Northern California
        elif lat > 33 and lat < 36 and lng > -120 and lng < -116:
            return "SCE"  # Southern California
        elif lat > 25 and lat < 28 and lng > -82 and lng < -80:
            return "FPL"  # South Florida
        elif lat > 40 and lat < 42 and lng > -74 and lng < -73:
            return "CONED"  # New York
        else:
            return "PGE"  # Default
    
    async def populate_form(self, job_id: str, form_type: str,
                          universal_data: Dict) -> Dict:
        """Convert universal form data to utility-specific format"""
        
        # Get job and its utility
        query = """
            SELECT j.*, u.code as utility_code
            FROM jobs_universal j
            LEFT JOIN utilities_master u ON u.id = j.detected_utility_id
            WHERE j.id = $1::uuid
        """
        
        async with self.db_pool.acquire() as conn:
            job = await conn.fetchrow(query, job_id)
        
        if not job:
            raise ValueError(f"Job {job_id} not found")
        
        utility_code = job['utility_code'] or 'PGE'
        
        # Get form template and mappings
        query = """
            SELECT ft.*, ufm.field_mappings
            FROM form_templates ft
            LEFT JOIN utility_form_mappings ufm ON 
                ufm.form_template_id = ft.id AND
                ufm.utility_id = (SELECT id FROM utilities_master WHERE code = $1)
            WHERE ft.form_type = $2
        """
        
        async with self.db_pool.acquire() as conn:
            template = await conn.fetchrow(query, utility_code, form_type)
        
        if not template:
            raise ValueError(f"No template for form type: {form_type}")
        
        # Apply field mappings
        field_mappings = json.loads(template['field_mappings']) if template['field_mappings'] else {}
        utility_data = {}
        
        for universal_field, value in universal_data.items():
            # Get utility-specific field name
            utility_field = field_mappings.get(universal_field, universal_field)
            utility_data[utility_field] = value
        
        # Validate against standards
        validation = await self._validate_form_data(
            utility_data, utility_code, form_type
        )
        
        # Store submission
        submission_id = str(uuid4())
        query = """
            INSERT INTO form_submissions (
                id, job_id, form_template_id, universal_data,
                utility_specific_data, validation_status, validation_results
            ) VALUES ($1, $2::uuid, $3, $4, $5, $6, $7)
        """
        
        async with self.db_pool.acquire() as conn:
            await conn.execute(
                query,
                submission_id,
                job_id,
                template['id'],
                json.dumps(universal_data),
                json.dumps(utility_data),
                'valid' if validation['is_valid'] else 'errors',
                json.dumps(validation)
            )
        
        return {
            "submission_id": submission_id,
            "job_id": job_id,
            "utility": utility_code,
            "form_type": form_type,
            "utility_format": utility_data,
            "validation": validation
        }
    
    async def _validate_form_data(self, data: Dict, utility_code: str,
                                 form_type: str) -> Dict:
        """Validate form data against utility standards"""
        
        errors = []
        warnings = []
        
        # Get relevant standards for this utility
        utility = self.utility_cache.get(utility_code, {})
        utility_id = utility.get('id')
        
        if utility_id:
            query = """
                SELECT * FROM standards_data_lake
                WHERE utility_id = $1
                AND standard_category IN ('CLEARANCE', 'SAFETY')
                LIMIT 10
            """
            
            async with self.db_pool.acquire() as conn:
                standards = await conn.fetch(query, utility_id)
            
            # Check clearances if present in form
            if 'clearance_horizontal' in data:
                clearance_value = float(data['clearance_horizontal'])
                # Check against standards
                for standard in standards:
                    req_values = json.loads(standard['requirement_value'])
                    if 'distances' in req_values:
                        for distance in req_values['distances']:
                            if distance.get('unit') in ['feet', 'ft']:
                                min_clearance = distance.get('value', 10)
                                if clearance_value < min_clearance:
                                    errors.append({
                                        'field': 'clearance_horizontal',
                                        'message': f'Below minimum {min_clearance} ft',
                                        'reference': standard['utility_reference']
                                    })
        
        return {
            'is_valid': len(errors) == 0,
            'errors': errors,
            'warnings': warnings,
            'checked_at': datetime.utcnow().isoformat()
        }
    
    async def cross_reference_standards(self, query_text: str) -> Dict:
        """Find equivalent standards across all utilities"""
        
        # Generate embedding for query
        query_embedding = self.embedder.encode(query_text).tolist()
        
        # Find similar standards across all utilities
        # Using cosine similarity approximation
        query = """
            SELECT s.*, u.code as utility_code, u.name as utility_name,
                   s.utility_reference, s.requirement_value
            FROM standards_data_lake s
            JOIN utilities_master u ON u.id = s.utility_id
            ORDER BY s.created_at DESC
            LIMIT 20
        """
        
        async with self.db_pool.acquire() as conn:
            results = await conn.fetch(query)
        
        # Group by utility
        by_utility = {}
        for result in results:
            utility = result['utility_code']
            if utility not in by_utility:
                by_utility[utility] = []
            
            by_utility[utility].append({
                'requirement': result['requirement_text'][:200],
                'reference': result['utility_reference'],
                'values': json.loads(result['requirement_value']) if result['requirement_value'] else {}
            })
        
        return {
            'query': query_text,
            'utilities_found': len(by_utility),
            'standards_by_utility': by_utility,
            'timestamp': datetime.utcnow().isoformat()
        }
    
    async def get_stats(self) -> Dict:
        """Get system statistics"""
        
        async with self.db_pool.acquire() as conn:
            stats = {}
            
            # Count utilities
            stats['utilities'] = await conn.fetchval(
                "SELECT COUNT(*) FROM utilities_master"
            )
            
            # Count standards
            stats['total_standards'] = await conn.fetchval(
                "SELECT COUNT(*) FROM standards_data_lake"
            )
            
            # Standards by utility
            utility_counts = await conn.fetch("""
                SELECT u.code, COUNT(s.id) as count
                FROM utilities_master u
                LEFT JOIN standards_data_lake s ON s.utility_id = u.id
                GROUP BY u.code
            """)
            
            stats['by_utility'] = {
                row['code']: row['count'] for row in utility_counts
            }
            
            # Count jobs
            stats['total_jobs'] = await conn.fetchval(
                "SELECT COUNT(*) FROM jobs_universal"
            )
            
            # Count forms
            stats['total_forms'] = await conn.fetchval(
                "SELECT COUNT(*) FROM form_submissions"
            )
            
            return stats

# Global instance
engine = UniversalEngine()
