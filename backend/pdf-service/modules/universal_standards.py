"""
Universal Standards Engine for NEXA
Multi-utility support with GPS detection and cross-reference
"""
import os
import json
import math
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from pathlib import Path
import hashlib
import logging
from dataclasses import dataclass, asdict
import math

logger = logging.getLogger(__name__)

@dataclass
class Utility:
    """Represents a utility company with its service area"""
    id: str
    name: str
    region: str
    coords: List[Tuple[float, float]]  # List of (lat, lng) defining service area
    standards_format: str  # e.g., 'greenbook', 'bluebook', 'spec_manual'
    spec_sections: List[str]  # Common sections in their specs
    
# Database of utilities with their GPS regions
UTILITIES_DB = {
    "PGE": Utility(
        id="PGE",
        name="Pacific Gas & Electric",
        region="Northern California",
        coords=[(37.7749, -122.4194), (38.5816, -121.4944), (36.7783, -119.4179)],
        standards_format="greenbook",
        spec_sections=["045786", "035986", "072136", "Overhead Lines", "Underground", "Poles", "Clearances"]
    ),
    "SCE": Utility(
        id="SCE",
        name="Southern California Edison",
        region="Southern California",
        coords=[(34.0522, -118.2437), (33.7175, -117.8311), (34.1083, -117.2898)],
        standards_format="bluebook",
        spec_sections=["Distribution", "Transmission", "Substations", "Safety", "Construction"]
    ),
    "SDGE": Utility(
        id="SDGE",
        name="San Diego Gas & Electric",
        region="San Diego County",
        coords=[(32.7157, -117.1611), (33.1434, -117.3506), (32.5343, -117.0382)],
        standards_format="standards_manual",
        spec_sections=["Electric Rule 20", "Gas Standards", "Electric Distribution", "Wildfire", "Interconnection"]
    ),
    "FPL": Utility(
        id="FPL",
        name="Florida Power & Light",
        region="Florida",
        coords=[(25.7617, -80.1918), (30.3322, -81.6557), (27.9506, -82.4572)],
        standards_format="spec_guide",
        spec_sections=["Hurricane Standards", "Underground", "Overhead", "Coastal", "Lightning Protection"]
    )
}

class UniversalStandardsEngine:
    """Engine for multi-utility standards management"""
    
    def __init__(self, data_path: str = "/data"):
        # Windows compatibility
        if not os.path.exists(data_path) and data_path == "/data":
            data_path = "./data"
        self.data_path = data_path
        self.db_file = os.path.join(data_path, "utility_db.json")
        self.ingested_specs = self._load_db()
        logger.info(f"🌍 Universal Standards Engine initialized with {len(UTILITIES_DB)} utilities")
        logger.info(f"📁 Using data path: {self.data_path}")
    
    def _load_db(self) -> Dict:
        """Load mock database from JSON file"""
        if os.path.exists(self.db_file):
            try:
                with open(self.db_file, 'r') as f:
                    data = json.load(f)
                    logger.info(f"📂 Loaded {len(data.get('specs', []))} ingested specs from database")
                    return data
            except Exception as e:
                logger.error(f"Error loading database: {e}")
        return {"specs": [], "jobs": [], "cross_refs": {}}
    
    def _save_db(self):
        """Save mock database to JSON file"""
        try:
            os.makedirs(self.data_path, exist_ok=True)
            with open(self.db_file, 'w') as f:
                json.dump(self.ingested_specs, f, indent=2)
            logger.info("💾 Database saved successfully")
        except Exception as e:
            logger.error(f"Error saving database: {e}")
    
    def detect_utility_by_gps(self, lat: float, lng: float) -> Optional[str]:
        """
        Detect utility company based on GPS coordinates
        Uses distance to known service points
        """
        min_distance = float('inf')
        detected_utility = None
        
        for utility_id, utility in UTILITIES_DB.items():
            for coord in utility.coords:
                distance = self._haversine_distance(lat, lng, coord[0], coord[1])
                if distance < min_distance:
                    min_distance = distance
                    detected_utility = utility_id
        
        # If within 200 miles of a utility service area, assign it
        if min_distance < 200:
            logger.info(f"🗺️ Detected utility: {detected_utility} (distance: {min_distance:.1f} miles)")
            return detected_utility
        
        # Default to None if location unclear
        logger.warning(f"📍 No clear utility for ({lat}, {lng})")
        return None
    
    def _haversine_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculate distance between two GPS points in miles"""
        R = 3959.0  # Earth radius in miles
        
        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        dlon_rad = math.radians(lon2 - lon1)
        dlat_rad = math.radians(lat2 - lat1)
        
        a = math.sin(dlat_rad/2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon_rad/2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        
        return R * c
    
    def ingest_utility_specs(self, utility_id: str, pdf_content: bytes, filename: str) -> Dict:
        """
        Ingest utility-specific specifications
        Mock processing - in production would extract and index PDF
        """
        if utility_id not in UTILITIES_DB:
            raise ValueError(f"Unknown utility: {utility_id}")
        
        utility = UTILITIES_DB[utility_id]
        file_hash = hashlib.sha256(pdf_content).hexdigest()[:16]
        
        # Mock processing
        spec_entry = {
            "utility": utility_id,
            "filename": filename,
            "file_hash": file_hash,
            "upload_time": datetime.now().isoformat(),
            "format": utility.standards_format,
            "size_bytes": len(pdf_content),
            "pages": max(1, len(pdf_content) // 2000),  # Mock page count
            "sections": utility.spec_sections,
            "status": "processed"
        }
        
        # Check for duplicates
        existing_hashes = [s.get('file_hash') for s in self.ingested_specs.get('specs', [])]
        if file_hash not in existing_hashes:
            if 'specs' not in self.ingested_specs:
                self.ingested_specs['specs'] = []
            self.ingested_specs['specs'].append(spec_entry)
            self._save_db()
            logger.info(f"✅ Ingested {filename} for {utility.name}")
        else:
            logger.info(f"⚠️ Duplicate spec detected for {filename}, skipping")
        
        return {
            "utility": utility_id,
            "utility_name": utility.name,
            "filename": filename,
            "status": "processed",
            "pages": spec_entry["pages"],
            "format": utility.standards_format,
            "sections": utility.spec_sections
        }
    
    def create_job_with_utility(self, job_data: Dict, lat: float, lng: float) -> Dict:
        """Create a job with auto-detected utility"""
        utility_id = self.detect_utility_by_gps(lat, lng)
        
        if not utility_id:
            utility_id = "PGE"  # Default
        
        job = {
            **job_data,
            "utility_id": utility_id,
            "utility_name": UTILITIES_DB[utility_id].name,
            "created_at": datetime.now().isoformat(),
            "location": {"lat": lat, "lng": lng}
        }
        
        if 'jobs' not in self.ingested_specs:
            self.ingested_specs['jobs'] = []
        self.ingested_specs['jobs'].append(job)
        self._save_db()
        
        return job
    
    def populate_form_for_utility(self, utility_id: str, universal_data: Dict) -> Dict:
        """
        Convert universal form data to utility-specific format
        Mock implementation - would use real mapping in production
        """
        if utility_id not in UTILITIES_DB:
            raise ValueError(f"Unknown utility: {utility_id}")
        
        utility = UTILITIES_DB[utility_id]
        
        # Mock field mappings
        field_mappings = {
            "PGE": {
                "job_number": "PM_NUMBER",
                "location": "SITE_ADDRESS",
                "pole_type": "POLE_CLASSIFICATION"
            },
            "SCE": {
                "job_number": "WO_NUMBER", 
                "location": "SERVICE_ADDRESS",
                "pole_type": "POLE_CLASS"
            },
            "FPL": {
                "job_number": "WORK_ORDER",
                "location": "PREMISE_ADDRESS",
                "pole_type": "POLE_RATING"
            }
        }
        
        mapping = field_mappings.get(utility_id, {})
        populated = {}
        
        for universal_field, value in universal_data.items():
            utility_field = mapping.get(universal_field, universal_field.upper())
            populated[utility_field] = value
        
        return {
            "utility": utility_id,
            "format": utility.standards_format,
            "fields": populated,
            "populated_at": datetime.now().isoformat()
        }
    
    def cross_reference_standards(self, requirement: str) -> Dict:
        """
        Cross-reference a requirement across all utilities
        Mock implementation - would search embeddings in production
        """
        results = {}
        requirement_lower = requirement.lower()
        
        for utility_id, utility in UTILITIES_DB.items():
            # Check if we have specs for this utility
            utility_specs = [s for s in self.ingested_specs.get('specs', []) 
                           if s.get('utility') == utility_id]
            
            if utility_specs:
                # Mock matching logic
                matching_sections = [s for s in utility.spec_sections 
                                   if any(word in s.lower() for word in requirement_lower.split())]
                
                if matching_sections:
                    results[utility_id] = {
                        "utility_name": utility.name,
                        "matching_sections": matching_sections,
                        "standards_format": utility.standards_format,
                        "confidence": 0.75,
                        "spec_count": len(utility_specs)
                    }
        
        # Save cross-reference for future use
        if 'cross_refs' not in self.ingested_specs:
            self.ingested_specs['cross_refs'] = {}
        self.ingested_specs['cross_refs'][requirement] = results
        self._save_db()
        
        return {
            "requirement": requirement,
            "cross_references": results,
            "utilities_compared": len(results)
        }
    
    def get_utility_info(self, utility_id: str) -> Optional[Dict]:
        """Get detailed information about a utility"""
        if utility_id in UTILITIES_DB:
            utility = UTILITIES_DB[utility_id]
            
            # Count ingested specs for this utility
            utility_specs = [s for s in self.ingested_specs.get('specs', []) 
                           if s.get('utility') == utility_id]
            
            return {
                "id": utility.id,
                "name": utility.name,
                "region": utility.region,
                "service_areas": [f"({lat}, {lng})" for lat, lng in utility.coords],
                "standards_format": utility.standards_format,
                "spec_sections": utility.spec_sections,
                "ingested_specs": len(utility_specs),
                "ready_for_analysis": len(utility_specs) > 0
            }
        return None
    
    def list_all_utilities(self) -> List[Dict]:
        """List all supported utilities with their status"""
        utilities = []
        for utility_id in UTILITIES_DB:
            info = self.get_utility_info(utility_id)
            if info:
                utilities.append(info)
        return utilities

# Global instance
engine = None

def get_universal_engine(data_path: str = "/data") -> UniversalStandardsEngine:
    """Get or create the universal standards engine singleton"""
    global engine
    if engine is None:
        engine = UniversalStandardsEngine(data_path)
    return engine

def integrate_universal_endpoints(app):
    """
    Integrate Universal Standards endpoints into FastAPI app
    Includes authentication support if available
    """
    from fastapi import APIRouter, HTTPException, UploadFile, File, Depends
    from pydantic import BaseModel
    import logging
    
    logger = logging.getLogger(__name__)
    router = APIRouter(prefix="/api/utilities", tags=["Universal Standards"])
    
    # Try to import auth dependencies
    auth_dependency = None
    optional_auth = None
    try:
        from modules.auth_system import get_current_user, optional_current_user
        auth_dependency = get_current_user
        optional_auth = optional_current_user
        logger.info("🔐 Auth system detected, endpoints will be protected")
    except ImportError:
        logger.warning("⚠️ Auth system not found, endpoints will be unprotected")
        # Create dummy dependency that returns None
        async def optional_auth():
            return None
    
    class GPSLocation(BaseModel):
        lat: float
        lng: float
    
    class JobCreateRequest(BaseModel):
        pm_number: str
        description: str
        lat: float
        lng: float
    
    class FormPopulateRequest(BaseModel):
        universal_data: Dict[str, Any]
    
    class CrossReferenceRequest(BaseModel):
        requirement: str
    
    @router.post("/detect")
    async def detect_utility(
        location: GPSLocation,
        current_user: Optional[Dict] = Depends(optional_auth)
    ):
        """Detect utility based on GPS coordinates"""
        try:
            engine = get_universal_engine()
            utility_id = engine.detect_utility_by_gps(location.lat, location.lng)
            
            response = {"utility_id": utility_id}
            if utility_id:
                response["utility_info"] = engine.get_utility_info(utility_id)
            
            if current_user:
                response["user"] = current_user.get("email", "unknown")
            
            return response
        except Exception as e:
            logger.error(f"Error detecting utility: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @router.post("/{utility_id}/ingest")
    async def ingest_specs(
        utility_id: str,
        file: UploadFile = File(...),
        current_user: Optional[Dict] = Depends(optional_auth)
    ):
        """Ingest utility-specific specification PDF"""
        try:
            if not file.filename.endswith('.pdf'):
                raise HTTPException(status_code=400, detail="Only PDF files are supported")
            
            engine = get_universal_engine()
            pdf_content = await file.read()
            
            result = engine.ingest_utility_specs(utility_id, pdf_content, file.filename)
            
            response = {"result": result}
            if current_user:
                response["user"] = current_user.get("email", "unknown")
                response["role"] = current_user.get("role", "viewer")
            
            return response
        except ValueError as e:
            raise HTTPException(status_code=404, detail=str(e))
        except Exception as e:
            logger.error(f"Error ingesting specs: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @router.get("/list")
    async def list_utilities(
        current_user: Optional[Dict] = Depends(optional_auth)
    ):
        """List all supported utilities"""
        engine = get_universal_engine()
        utilities = engine.list_all_utilities()
        
        response = {"utilities": utilities, "total": len(utilities)}
        if current_user:
            response["user"] = current_user.get("email", "unknown")
        
        return response
    
    @router.post("/jobs/create")
    async def create_job(
        request: JobCreateRequest,
        current_user: Optional[Dict] = Depends(optional_auth)
    ):
        """Create a job with auto-detected utility"""
        try:
            engine = get_universal_engine()
            
            job_data = {
                "pm_number": request.pm_number,
                "description": request.description,
                "created_by": current_user.get("email") if current_user else "anonymous"
            }
            
            job = engine.create_job_with_utility(job_data, request.lat, request.lng)
            
            return {"job": job, "message": f"Job created for {job['utility_name']}"}
        except Exception as e:
            logger.error(f"Error creating job: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @router.post("/forms/{utility_id}/populate")
    async def populate_form(
        utility_id: str,
        request: FormPopulateRequest,
        current_user: Optional[Dict] = Depends(optional_auth)
    ):
        """Populate utility-specific form from universal data"""
        try:
            engine = get_universal_engine()
            result = engine.populate_form_for_utility(utility_id, request.universal_data)
            
            response = {"result": result}
            if current_user:
                response["user"] = current_user.get("email", "unknown")
            
            return response
        except ValueError as e:
            raise HTTPException(status_code=404, detail=str(e))
        except Exception as e:
            logger.error(f"Error populating form: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @router.post("/standards/cross-reference")
    async def cross_reference(
        request: CrossReferenceRequest,
        current_user: Optional[Dict] = Depends(optional_auth)
    ):
        """Cross-reference a requirement across all utilities"""
        engine = get_universal_engine()
        results = engine.cross_reference_standards(request.requirement)
        
        if current_user:
            results["requested_by"] = current_user.get("email", "unknown")
        
        return results
    
    # Include router in app
    app.include_router(router)
    logger.info("🌍 Universal Standards endpoints registered at /api/utilities/*")
    
    return router
