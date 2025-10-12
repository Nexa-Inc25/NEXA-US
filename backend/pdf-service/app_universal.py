"""
NEXA Universal Standards Platform
Enhanced app with universal utility standards engine
"""
import os
import json
import logging
from typing import List, Dict, Optional
from datetime import datetime
from uuid import uuid4
from fastapi import FastAPI, UploadFile, File, HTTPException, Form, Depends
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import asyncpg

# Import existing modules
from universal_engine import engine, UniversalEngine

# Import existing analysis capabilities
try:
    from analyze_go_backs import analyze_go_backs_with_confidence
    from spec_embedder_module import SpecEmbedder
    from pole_vision_detector_clean import detector
except ImportError as e:
    logging.warning(f"Some modules not found: {e}")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="NEXA Universal Standards Platform",
    description="AI-powered universal utility standards and form automation",
    version="3.0"
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    """Initialize the universal engine on startup"""
    await engine.initialize()
    logger.info("✅ Universal Standards Engine initialized")
    
    # Show initial stats
    stats = await engine.get_stats()
    logger.info(f"📊 System Stats: {stats}")

@app.get("/")
async def root():
    """Root endpoint with system info"""
    stats = await engine.get_stats()
    return {
        "service": "NEXA Universal Standards Platform",
        "version": "3.0",
        "status": "operational",
        "capabilities": [
            "Universal standards ingestion",
            "Multi-utility support",
            "Automatic utility detection",
            "Smart form population",
            "Cross-utility analysis"
        ],
        "stats": stats
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        stats = await engine.get_stats()
        return {
            "status": "healthy",
            "utilities_loaded": stats.get('utilities', 0),
            "standards_count": stats.get('total_standards', 0),
            "engine": "operational"
        }
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}

# ==================== UTILITY MANAGEMENT ====================

@app.get("/api/utilities")
async def list_utilities():
    """List all configured utilities"""
    return {
        "utilities": list(engine.utility_cache.keys()),
        "details": engine.utility_cache
    }

@app.post("/api/utilities/{utility_code}/ingest")
async def ingest_utility_spec(
    utility_code: str,
    file: UploadFile = File(...)
):
    """Ingest and standardize a utility spec document"""
    
    if utility_code not in engine.utility_cache:
        raise HTTPException(404, f"Utility {utility_code} not configured")
    
    # Read PDF content
    content = await file.read()
    
    # Process with universal engine
    result = await engine.ingest_spec(
        utility_code=utility_code,
        pdf_content=content,
        filename=file.filename
    )
    
    logger.info(f"✅ Ingested spec for {utility_code}: {result}")
    
    return result

@app.post("/api/utilities/detect")
async def detect_utility(
    lat: float = Form(...),
    lng: float = Form(...),
    address: Optional[str] = Form(None)
):
    """Detect which utility serves a location"""
    
    utility_code = await engine.detect_utility_for_job(lat, lng, address)
    utility_info = engine.utility_cache.get(utility_code, {})
    
    return {
        "detected_utility": utility_code,
        "utility_name": utility_info.get('name'),
        "region": utility_info.get('region'),
        "coordinates": {"lat": lat, "lng": lng},
        "address": address
    }

# ==================== JOB MANAGEMENT ====================

@app.post("/api/jobs/create")
async def create_job(
    organization_id: str = Form(...),
    job_number: str = Form(...),
    lat: float = Form(...),
    lng: float = Form(...),
    address: Optional[str] = Form(None),
    job_type: str = Form("installation")
):
    """Create a job with automatic utility detection"""
    
    # Detect utility for location
    utility_code = await engine.detect_utility_for_job(lat, lng, address)
    utility = engine.utility_cache.get(utility_code, {})
    
    # Create job in database
    job_id = str(uuid4())
    
    query = """
        INSERT INTO jobs_universal (
            id, organization_id, job_number, location_lat, location_lng,
            address, detected_utility_id, job_type, status
        ) VALUES ($1, $2::uuid, $3, $4, $5, $6, $7, $8, $9)
        RETURNING id
    """
    
    async with engine.db_pool.acquire() as conn:
        # Get org ID (create if demo)
        org_id = organization_id
        if organization_id == "demo":
            org_id = await conn.fetchval(
                "SELECT id FROM organizations WHERE subdomain = 'demo'"
            )
        
        await conn.execute(
            query,
            job_id,
            org_id,
            job_number,
            lat,
            lng,
            address,
            utility.get('id'),
            job_type,
            'active'
        )
    
    return {
        "job_id": job_id,
        "job_number": job_number,
        "detected_utility": utility_code,
        "utility_name": utility.get('name'),
        "location": {"lat": lat, "lng": lng, "address": address},
        "status": "created"
    }

@app.get("/api/jobs/{job_id}")
async def get_job(job_id: str):
    """Get job details"""
    
    query = """
        SELECT j.*, u.code as utility_code, u.name as utility_name
        FROM jobs_universal j
        LEFT JOIN utilities_master u ON u.id = j.detected_utility_id
        WHERE j.id = $1::uuid
    """
    
    async with engine.db_pool.acquire() as conn:
        job = await conn.fetchrow(query, job_id)
    
    if not job:
        raise HTTPException(404, "Job not found")
    
    return dict(job)

# ==================== FORM MANAGEMENT ====================

@app.post("/api/forms/populate")
async def populate_form(
    job_id: str = Form(...),
    form_type: str = Form(...),
    form_data: str = Form(...)  # JSON string
):
    """Populate form with utility-specific format based on job location"""
    
    # Parse form data
    try:
        universal_data = json.loads(form_data)
    except json.JSONDecodeError:
        raise HTTPException(400, "Invalid JSON in form_data")
    
    # Process with engine
    result = await engine.populate_form(
        job_id=job_id,
        form_type=form_type,
        universal_data=universal_data
    )
    
    logger.info(f"✅ Form populated for job {job_id}: {result['utility']}")
    
    return result

@app.get("/api/forms/templates")
async def get_form_templates():
    """Get available form templates"""
    
    query = """
        SELECT form_type, universal_fields
        FROM form_templates
        ORDER BY form_type
    """
    
    async with engine.db_pool.acquire() as conn:
        templates = await conn.fetch(query)
    
    return {
        "templates": [
            {
                "form_type": t['form_type'],
                "fields": json.loads(t['universal_fields'])
            }
            for t in templates
        ]
    }

# ==================== CROSS-REFERENCE ANALYSIS ====================

@app.post("/api/standards/cross-reference")
async def cross_reference_standards(
    query: str = Form(...),
    source_utility: Optional[str] = Form(None)
):
    """Find equivalent standards across all utilities"""
    
    result = await engine.cross_reference_standards(query)
    
    return result

@app.get("/api/standards/search")
async def search_standards(
    q: str,
    utility: Optional[str] = None,
    category: Optional[str] = None
):
    """Search standards in the data lake"""
    
    query_parts = ["SELECT * FROM standards_data_lake WHERE 1=1"]
    params = []
    param_count = 0
    
    if utility:
        param_count += 1
        query_parts.append(f"AND utility_id = (SELECT id FROM utilities_master WHERE code = ${param_count})")
        params.append(utility)
    
    if category:
        param_count += 1
        query_parts.append(f"AND standard_category = ${param_count}")
        params.append(category)
    
    if q:
        param_count += 1
        query_parts.append(f"AND requirement_text ILIKE ${param_count}")
        params.append(f"%{q}%")
    
    query_parts.append("LIMIT 20")
    
    query = " ".join(query_parts)
    
    async with engine.db_pool.acquire() as conn:
        results = await conn.fetch(query, *params)
    
    return {
        "query": q,
        "results": [dict(r) for r in results],
        "count": len(results)
    }

# ==================== EXISTING ENDPOINTS (ENHANCED) ====================

@app.post("/analyze-audit")
async def analyze_audit(
    file: UploadFile = File(...),
    job_id: Optional[str] = Form(None)
):
    """Analyze audit with automatic utility detection"""
    
    # If job_id provided, get utility context
    utility_code = "PGE"  # Default
    
    if job_id:
        query = """
            SELECT u.code FROM jobs_universal j
            JOIN utilities_master u ON u.id = j.detected_utility_id
            WHERE j.id = $1::uuid
        """
        async with engine.db_pool.acquire() as conn:
            result = await conn.fetchval(query, job_id)
            if result:
                utility_code = result
    
    # Process with existing analysis (enhanced with utility context)
    try:
        content = await file.read()
        
        # Use existing analyze_go_backs function if available
        if 'analyze_go_backs_with_confidence' in globals():
            analysis = analyze_go_backs_with_confidence(content)
        else:
            analysis = {"message": "Analysis module not loaded"}
        
        # Enhance with utility context
        analysis['utility_context'] = {
            'utility': utility_code,
            'utility_name': engine.utility_cache.get(utility_code, {}).get('name'),
            'applied_standards': f"{utility_code} specifications"
        }
        
        if job_id:
            analysis['job_id'] = job_id
        
        return analysis
        
    except Exception as e:
        logger.error(f"Error analyzing audit: {e}")
        raise HTTPException(500, str(e))

@app.post("/vision/detect")
async def detect_poles(
    image: UploadFile = File(...),
    job_id: Optional[str] = Form(None)
):
    """Vision detection with utility context"""
    
    try:
        # Use existing vision detector if available
        if 'detector' in globals():
            image_content = await image.read()
            result = detector.detect_poles(image_content)
        else:
            result = {"message": "Vision module not loaded"}
        
        # Add job context if provided
        if job_id:
            result['job_id'] = job_id
        
        return result
        
    except Exception as e:
        logger.error(f"Error in vision detection: {e}")
        raise HTTPException(500, str(e))

# ==================== ADMIN & STATS ====================

@app.get("/api/stats")
async def get_statistics():
    """Get platform statistics"""
    stats = await engine.get_stats()
    
    # Add more detailed stats
    async with engine.db_pool.acquire() as conn:
        # Jobs by utility
        jobs_by_utility = await conn.fetch("""
            SELECT u.code, COUNT(j.id) as job_count
            FROM utilities_master u
            LEFT JOIN jobs_universal j ON j.detected_utility_id = u.id
            GROUP BY u.code
        """)
        
        stats['jobs_by_utility'] = {
            row['code']: row['job_count'] for row in jobs_by_utility
        }
        
        # Recent submissions
        recent_forms = await conn.fetchval("""
            SELECT COUNT(*) FROM form_submissions
            WHERE created_at > CURRENT_DATE - INTERVAL '7 days'
        """)
        
        stats['recent_submissions'] = recent_forms
    
    return stats

@app.post("/api/demo/setup")
async def setup_demo_data():
    """Setup demo data for testing"""
    
    # Create demo jobs for each utility
    demo_jobs = [
        {"lat": 37.7749, "lng": -122.4194, "address": "San Francisco, CA", "utility": "PGE"},
        {"lat": 34.0522, "lng": -118.2437, "address": "Los Angeles, CA", "utility": "SCE"},
        {"lat": 25.7617, "lng": -80.1918, "address": "Miami, FL", "utility": "FPL"},
        {"lat": 40.7128, "lng": -74.0060, "address": "New York, NY", "utility": "CONED"}
    ]
    
    created_jobs = []
    
    for job_data in demo_jobs:
        job = await create_job(
            organization_id="demo",
            job_number=f"DEMO-{job_data['utility']}-001",
            lat=job_data['lat'],
            lng=job_data['lng'],
            address=job_data['address'],
            job_type="installation"
        )
        created_jobs.append(job)
    
    return {
        "message": "Demo data created",
        "jobs_created": len(created_jobs),
        "jobs": created_jobs
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
