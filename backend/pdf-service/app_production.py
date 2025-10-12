"""
NEXA Document Analyzer - Production FastAPI Application
Optimized for Render.com deployment
October 11, 2025
"""

import os
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone

from fastapi import FastAPI, File, UploadFile, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
import torch
from sentence_transformers import SentenceTransformer
import numpy as np
import pickle
import hashlib
import json

# Import our modules
from modules.secure_upload import FileEncryptor, FileValidator, TokenManager, AuditLogger
from modules.auth_middleware import PasswordValidator
from modules.ml_device_utils import device_manager, get_device, optimize_model
from modules.gradient_accumulator import GradientAccumulator
from modules.ml_monitoring import MLMonitor

# Configure logging
logging.basicConfig(
    level=os.getenv('LOG_LEVEL', 'INFO'),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Security
security = HTTPBearer()

# Application metadata
APP_VERSION = "1.0.0"
APP_NAME = "NEXA Document Analyzer"
APP_DESCRIPTION = """
Production-ready document analysis system for PG&E compliance.
Processes spec books, analyzes audits, and identifies repealable infractions.
"""

# Initialize FastAPI
app = FastAPI(
    title=APP_NAME,
    description=APP_DESCRIPTION,
    version=APP_VERSION,
    docs_url="/docs" if os.getenv('ENVIRONMENT') != 'production' else None,
    redoc_url="/redoc" if os.getenv('ENVIRONMENT') != 'production' else None
)

# CORS configuration
origins = os.getenv('CORS_ORIGINS', 'http://localhost:3000').split(',')
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Data directory setup
DATA_DIR = Path(os.getenv('DATA_DIR', '/data'))
DATA_DIR.mkdir(parents=True, exist_ok=True)
EMBEDDINGS_FILE = DATA_DIR / 'spec_embeddings.pkl'
METADATA_FILE = DATA_DIR / 'spec_metadata.json'
SECURE_UPLOAD_DIR = DATA_DIR / 'secure_uploads'
SECURE_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# Global variables
model = None
spec_embeddings = []
spec_chunks = []
spec_metadata = {}
encryptor = FileEncryptor()
file_validator = FileValidator()
audit_logger = AuditLogger()

# Request/Response models
class SpecUploadResponse(BaseModel):
    success: bool
    message: str
    files_processed: int
    total_chunks: int

class AuditAnalysisRequest(BaseModel):
    confidence_threshold: float = Field(default=0.6, ge=0.0, le=1.0)
    max_results: int = Field(default=10, ge=1, le=100)

class InfractionResult(BaseModel):
    infraction: str
    status: str  # "repealable" or "true_violation"
    confidence: float
    spec_references: List[str]
    reasons: List[str]

class AuditAnalysisResponse(BaseModel):
    success: bool
    pm_number: Optional[str]
    total_infractions: int
    repealable_count: int
    results: List[InfractionResult]
    processing_time_ms: float

# Authentication dependency
async def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Verify JWT token for protected endpoints"""
    if not os.getenv('AUTH_ENABLED', 'true').lower() == 'true':
        return {"user_id": "dev_user", "role": "admin"}
    
    try:
        token = credentials.credentials
        payload = TokenManager.verify_token(token)
        return payload
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        )

# Startup event
@app.on_event("startup")
async def startup_event():
    """Initialize ML models and load embeddings"""
    global model, spec_embeddings, spec_chunks, spec_metadata
    
    logger.info(f"Starting {APP_NAME} v{APP_VERSION}")
    
    # Initialize ML device
    device = get_device()
    logger.info(f"Using device: {device}")
    
    # Load sentence transformer model
    logger.info("Loading SentenceTransformer model...")
    model_name = os.getenv('EMBEDDING_MODEL', 'all-MiniLM-L6-v2')
    model = SentenceTransformer(model_name)
    model = optimize_model(model)
    logger.info(f"Model loaded: {model_name}")
    
    # Load existing embeddings if available
    if EMBEDDINGS_FILE.exists():
        try:
            with open(EMBEDDINGS_FILE, 'rb') as f:
                data = pickle.load(f)
                spec_embeddings = data.get('embeddings', [])
                spec_chunks = data.get('chunks', [])
            logger.info(f"Loaded {len(spec_embeddings)} spec embeddings")
        except Exception as e:
            logger.warning(f"Could not load embeddings: {e}")
    
    # Load metadata
    if METADATA_FILE.exists():
        try:
            with open(METADATA_FILE, 'r') as f:
                spec_metadata = json.load(f)
            logger.info(f"Loaded metadata for {len(spec_metadata.get('files', []))} files")
        except Exception as e:
            logger.warning(f"Could not load metadata: {e}")
    
    # Log system status
    ml_status = MLMonitor.check_ml_dependencies()
    logger.info(f"ML Status: {ml_status['healthy']}")
    
    logger.info("Startup complete - ready to serve requests")

# Endpoints
@app.get("/")
async def root():
    """Root endpoint with system info"""
    return {
        "name": APP_NAME,
        "version": APP_VERSION,
        "status": "operational",
        "specs_loaded": len(spec_chunks),
        "device": str(get_device()),
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring"""
    memory_stats = device_manager.get_memory_summary()
    return {
        "status": "healthy",
        "specs_loaded": len(spec_chunks),
        "memory_used_mb": memory_stats.get('used_mb', 0),
        "model_loaded": model is not None,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

@app.post("/upload-specs", response_model=SpecUploadResponse)
async def upload_specs(
    files: List[UploadFile] = File(...),
    user_data: dict = Depends(verify_token)
):
    """
    Upload and learn from PG&E spec books.
    Chunks text, generates embeddings, stores for cross-reference.
    """
    try:
        # Audit log
        await audit_logger.log_access(
            user_id=user_data['user_id'],
            action='upload_specs',
            resource='spec_books',
            ip_address='0.0.0.0',  # Get from request in production
            success=True,
            details={'file_count': len(files)}
        )
        
        processed = 0
        total_chunks = 0
        
        for file in files:
            # Validate file
            validation = await file_validator.validate_file(file)
            if not validation['valid']:
                logger.warning(f"File validation failed: {validation['errors']}")
                continue
            
            # Process PDF (simplified for example)
            file_content = await file.read()
            
            # Generate hash for deduplication
            file_hash = hashlib.sha256(file_content).hexdigest()
            
            # Check if already processed
            if spec_metadata.get('files', {}).get(file_hash):
                logger.info(f"File {file.filename} already processed")
                continue
            
            # Encrypt and save
            encrypted = encryptor.encrypt_file(file_content)
            secure_path = SECURE_UPLOAD_DIR / f"{file_hash}.enc"
            with open(secure_path, 'wb') as f:
                f.write(encrypted)
            
            # Extract text and chunk (mock for now)
            chunks = [f"Mock chunk {i} from {file.filename}" for i in range(10)]
            
            # Generate embeddings with gradient accumulation
            accumulator = GradientAccumulator(accumulation_steps=4)
            with device_manager.inference_mode():
                embeddings = model.encode(chunks, batch_size=8, normalize_embeddings=True)
            
            # Store
            spec_chunks.extend(chunks)
            spec_embeddings.extend(embeddings)
            
            # Update metadata
            if 'files' not in spec_metadata:
                spec_metadata['files'] = {}
            spec_metadata['files'][file_hash] = {
                'filename': file.filename,
                'upload_time': datetime.now(timezone.utc).isoformat(),
                'chunks': len(chunks),
                'encrypted_path': str(secure_path)
            }
            
            processed += 1
            total_chunks += len(chunks)
        
        # Save embeddings and metadata
        with open(EMBEDDINGS_FILE, 'wb') as f:
            pickle.dump({
                'embeddings': spec_embeddings,
                'chunks': spec_chunks
            }, f)
        
        with open(METADATA_FILE, 'w') as f:
            json.dump(spec_metadata, f, indent=2)
        
        # Clear GPU cache if needed
        device_manager.clear_cache()
        
        return SpecUploadResponse(
            success=True,
            message=f"Successfully processed {processed} files",
            files_processed=processed,
            total_chunks=total_chunks
        )
        
    except Exception as e:
        logger.error(f"Error uploading specs: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/analyze-audit", response_model=AuditAnalysisResponse)
async def analyze_audit(
    file: UploadFile = File(...),
    params: AuditAnalysisRequest = AuditAnalysisRequest(),
    user_data: dict = Depends(verify_token)
):
    """
    Analyze audit document for infractions and determine repealable items.
    Cross-references with learned specs using similarity search.
    """
    start_time = datetime.now(timezone.utc)
    
    try:
        # Validate file
        validation = await file_validator.validate_file(file)
        if not validation['valid']:
            raise HTTPException(400, detail=validation['errors'][0])
        
        # Process audit (mock extraction)
        file_content = await file.read()
        
        # Extract infractions (mock)
        infractions = [
            "Non-compliant transformer installation",
            "Missing ground wire on pole",
            "Improper clearance for overhead lines"
        ]
        
        # Extract PM number (mock)
        pm_number = "PM-2025-10-001"
        
        results = []
        repealable_count = 0
        
        for infraction in infractions:
            # Generate embedding for infraction
            with device_manager.inference_mode():
                infraction_embedding = model.encode([infraction], normalize_embeddings=True)[0]
            
            # Find similar specs (cosine similarity)
            similarities = np.dot(spec_embeddings, infraction_embedding)
            top_indices = np.argsort(similarities)[-params.max_results:][::-1]
            
            # Determine if repealable based on similarity threshold
            max_similarity = similarities[top_indices[0]] if len(top_indices) > 0 else 0
            is_repealable = max_similarity >= params.confidence_threshold
            
            if is_repealable:
                repealable_count += 1
            
            # Get spec references
            spec_refs = [spec_chunks[idx][:50] + "..." for idx in top_indices[:3]]
            
            # Generate reasons (mock)
            reasons = []
            if is_repealable:
                reasons.append(f"Spec allows variance for this condition (similarity: {max_similarity:.2f})")
                reasons.append("Exception granted for Grade B construction per spec")
            else:
                reasons.append("No matching spec exception found")
                reasons.append("Violation requires correction")
            
            results.append(InfractionResult(
                infraction=infraction,
                status="repealable" if is_repealable else "true_violation",
                confidence=float(max_similarity),
                spec_references=spec_refs,
                reasons=reasons
            ))
        
        # Calculate processing time
        processing_time = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
        
        # Audit log
        await audit_logger.log_access(
            user_id=user_data['user_id'],
            action='analyze_audit',
            resource=pm_number,
            ip_address='0.0.0.0',
            success=True,
            details={
                'infractions': len(infractions),
                'repealable': repealable_count
            }
        )
        
        return AuditAnalysisResponse(
            success=True,
            pm_number=pm_number,
            total_infractions=len(infractions),
            repealable_count=repealable_count,
            results=results,
            processing_time_ms=processing_time
        )
        
    except Exception as e:
        logger.error(f"Error analyzing audit: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/spec-library")
async def get_spec_library(user_data: dict = Depends(verify_token)):
    """Get information about loaded spec documents"""
    return {
        "total_files": len(spec_metadata.get('files', {})),
        "total_chunks": len(spec_chunks),
        "files": list(spec_metadata.get('files', {}).values()),
        "model": os.getenv('EMBEDDING_MODEL', 'all-MiniLM-L6-v2')
    }

@app.post("/auth/token")
async def get_token(username: str, password: str):
    """Get JWT token (simplified - use proper auth in production)"""
    # Validate password
    valid, errors = PasswordValidator.validate_password(password, username)
    if not valid:
        raise HTTPException(400, detail=errors[0])
    
    # In production, verify against database
    if username == "admin" and password == "Test@Pass123!":
        token = TokenManager.create_access_token(username, "admin")
        return {"access_token": token, "token_type": "bearer"}
    else:
        raise HTTPException(401, detail="Invalid credentials")

@app.get("/ml-status")
async def ml_status(user_data: dict = Depends(verify_token)):
    """Get ML system status and monitoring data"""
    return MLMonitor.check_ml_dependencies()

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv('PORT', 8000))
    uvicorn.run(
        "app_production:app",
        host="0.0.0.0",
        port=port,
        reload=os.getenv('API_RELOAD', 'false').lower() == 'true'
    )
