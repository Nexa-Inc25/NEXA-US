"""
NEXA AI Document Analyzer - October 2025 Enhanced Version
Enhanced with FuseSaver, TripSaver, Reclosers, SCADA-Mate SD support
Improved OCR cleaning for audit garble and increased file limits
"""
import os
import io
import pickle
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sentence_transformers import SentenceTransformer, util
from pypdf import PdfReader
import nltk
import re
import torch
import pandas as pd
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, validator
import pytesseract
from PIL import Image
import logging
import time
from multiprocessing import Pool, cpu_count
from middleware import ValidationMiddleware, ErrorHandlingMiddleware, RateLimitMiddleware

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# === CPU PERFORMANCE OPTIMIZATION ===
# Detect available cores and optimize threading for CPU-only inference
num_cores = int(os.environ.get('RENDER_CORES', len(os.sched_getaffinity(0)) if hasattr(os, 'sched_getaffinity') else cpu_count()))
optimal_threads = max(1, num_cores // 2)  # Use half cores to avoid oversubscription

# Set PyTorch threading for optimal CPU performance
torch.set_num_threads(optimal_threads)
torch.set_num_interop_threads(1)  # Minimize for inference

# Enable oneDNN/MKL optimizations
os.environ.setdefault('OMP_NUM_THREADS', str(optimal_threads))
os.environ.setdefault('MKL_NUM_THREADS', str(optimal_threads))
os.environ.setdefault('PYTORCH_ENABLE_MPS_FALLBACK', '1')

logger.info(f"⚡ CPU Optimization: {num_cores} cores detected, using {optimal_threads} threads")
logger.info(f"⚡ PyTorch threads: {torch.get_num_threads()}, Inter-op threads: {torch.get_num_interop_threads()}")

# Log PyTorch configuration for debugging
if logger.level <= logging.DEBUG:
    logger.debug(f"PyTorch config: {torch.__config__.show()}")

# Performance monitoring
class PerformanceMonitor:
    def __init__(self):
        self.timings = {}
    
    def start(self, operation: str):
        self.timings[operation] = time.time()
    
    def end(self, operation: str) -> float:
        if operation in self.timings:
            elapsed = time.time() - self.timings[operation]
            logger.info(f"⏱️ {operation}: {elapsed:.2f}s")
            del self.timings[operation]
            return elapsed
        return 0.0

perf_monitor = PerformanceMonitor()

# Download NLTK data
nltk.download('punkt', quiet=True)

app = FastAPI(
    title="NEXA AI Document Analyzer",
    description="Enterprise-grade document analysis for spec compliance with enhanced FuseSaver/Reclosers support",
    version="1.0.0 (October 2025 Enhanced)",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add middleware stack (order matters - executed in reverse)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add custom middleware
app.add_middleware(RateLimitMiddleware, calls=100, period=60)  # 100 requests per minute
app.add_middleware(ErrorHandlingMiddleware)
app.add_middleware(ValidationMiddleware)

# Mount static files if directory exists
static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(static_dir):
    os.makedirs(static_dir, exist_ok=True)
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

# Model setup (force CPU for Render deployment)
device = 'cpu'  # Always use CPU for consistent performance on Render
logger.info(f"🔧 Using device: {device}")

# Load model with performance monitoring
perf_monitor.start("Model loading")
model = SentenceTransformer('all-MiniLM-L6-v2', device=device)
perf_monitor.end("Model loading")

# Persistence (use /data for Render disk if available)
EMBEDDINGS_PATH = '/data/spec_embeddings.pkl' if os.path.exists('/data') else 'spec_embeddings.pkl'
logger.info(f"💾 Embeddings will be stored at: {EMBEDDINGS_PATH}")

# Enhanced PG&E patterns for better extraction
PGE_PATTERNS = {
    'document_number': r'Document\s+(\d{5,6})|TD-\d+P-\d+',
    'revision': r'Rev\.\s*#?\s*(\d+)',
    'effective_date': r'Effective\s+Date:\s*([\d/]+)',
    'purpose': r'Purpose\s+and\s+Scope',
    'references': r'References?:',
    'table': r'Table\s+\d+',
    'figure': r'Figure\s+\d+',
    'notes': r'General\s+Notes?|Notes?:',
    'electric_dist': r'Electric\s+Distribution',
    'oh_switches': r'OH:\s*Switches|FRO:\s*OH\s*Switches',
    'fuse_saver': r'FuseSaver|Fuse\s+Saver',
    'trip_saver': r'TripSaver|Trip\s+Saver',
    'scada': r'SCADA(?:-Mate\s+SD)?',
    'recloser': r'[Ll]ine\s+[Rr]ecloser[s]?|[Rr]ecloser[s]?',
}

class InfractionAnalysis(BaseModel):
    infraction: str = Field(..., min_length=1, max_length=500)
    status: str = Field(..., regex='^(REPEALABLE|NOT_REPEALABLE|MAYBE_REPEALABLE)$')
    confidence: float = Field(..., ge=0.0, le=100.0, description="Confidence percentage (0-100)")
    match_count: int = Field(..., ge=0, description="Number of matching specs")
    reasons: List[str] = Field(default_factory=list, description="Reasons for the determination")
    
    @validator('confidence')
    def round_confidence(cls, v):
        return round(v, 1)

class SpecUploadResponse(BaseModel):
    message: str = Field(..., min_length=1)
    chunks_learned: int = Field(..., ge=0)
    storage_path: str = Field(..., min_length=1)
    timestamp: Optional[str] = Field(None, description="Upload timestamp")

class AuditAnalysisRequest(BaseModel):
    """Request model for audit analysis with validation"""
    max_infractions: int = Field(default=100, ge=1, le=500, description="Maximum infractions to process")
    confidence_threshold: float = Field(default=0.5, ge=0.0, le=1.0, description="Confidence threshold")

def clean_audit_garble(text: str) -> str:
    """Enhanced cleaning for audit text garble"""
    original_length = len(text)
    
    # Fix common OCR issues
    text = re.sub(r'andentercallsnotlistedatendofeachsection\.\)No', '', text)
    text = re.sub(r'(\w)\s+(\w)', r'\1\2', text)  # Fix split words
    text = re.sub(r'\s+', ' ', text)  # Normalize spaces
    text = re.sub(r'\)\.?No', '', text)  # Remove common audit endings
    text = re.sub(r'QCInspection', 'QC Inspection', text)
    text = re.sub(r'Go-back:|Goback:', 'Go-back:', text)
    
    # Log cleaning results if significant changes
    if len(text) < original_length * 0.9:
        logger.info(f"🧹 Cleaned audit text: reduced from {original_length} to {len(text)} chars")
    
    return text.strip()

def extract_text_from_pdf(file_content: bytes, use_ocr: bool = False) -> str:
    """Extract text from PDF with enhanced OCR support"""
    try:
        reader = PdfReader(io.BytesIO(file_content))
        text_parts = []
        ocr_pages = 0
        
        for page_num, page in enumerate(reader.pages, 1):
            page_text = page.extract_text()
            
            # If no text extracted and OCR is enabled
            if (not page_text or len(page_text.strip()) < 50) and use_ocr:
                try:
                    # Try to extract images from the page
                    for image_obj in page.images:
                        img = Image.open(io.BytesIO(image_obj.data))
                        ocr_text = pytesseract.image_to_string(img)
                        if ocr_text:
                            page_text = f"[OCR Page {page_num}]\n{ocr_text}"
                            ocr_pages += 1
                            logger.info(f"OCR extracted text from page {page_num}")
                            break
                except Exception as ocr_error:
                    logger.warning(f"OCR failed for page {page_num}: {str(ocr_error)}")
            
            if page_text:
                # Clean audit garble
                page_text = clean_audit_garble(page_text)
                
                # Add PG&E document markers if found
                doc_match = re.search(PGE_PATTERNS['document_number'], page_text)
                if doc_match:
                    page_text = f"[Document {doc_match.group(0)}]\n{page_text}"
                
                text_parts.append(page_text)
        
        if ocr_pages > 0:
            logger.info(f"OCR was used on {ocr_pages} pages")
        
        return '\n'.join(text_parts)
    
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"PDF extraction failed: {str(e)}")

def chunk_text(text: str, chunk_size: int = 1100) -> List[str]:
    """Enhanced chunking for FuseSaver/Recloser detailed docs"""
    # Enhanced section patterns
    section_patterns = [
        r'Rev\. #\d+:',
        r'Purpose and Scope',
        r'General Notes',
        r'References',
        r'Table \d+',
        r'Figure \d+',
        r'Greenbook',
        r'UG-1',
        r'ampacity',
        r'Electric Planning Manual',
        r'Enclosures/Greenbook',
        r'OH: Capacitors',
        r'OH: Cutouts/Fuses',
        r'FRO: Capacitors',
        r'OH: Switches',
        r'FRO: OH Switches',
        r'TD-\d+P-\d+',
        r'Electric Distribution',
        r'FuseSaver',
        r'TripSaver',
        r'SCADA-Mate SD',
        r'line recloser[s]?',
        r'bypass switch[es]?',
        r'sectionalizer[s]?',
    ]
    
    combined_pattern = '(' + '|'.join(section_patterns) + ')'
    sections = re.split(combined_pattern, text, flags=re.IGNORECASE)
    
    chunks = []
    current = ''
    
    for section in sections:
        if not section:
            continue
            
        if len(current) + len(section) > chunk_size:
            if current.strip():
                chunks.append(current.strip())
            current = section
        else:
            current += ' ' + section
    
    if current.strip():
        chunks.append(current.strip())
    
    return chunks

def learn_spec_book(file_content: bytes, use_ocr: bool = False) -> dict:
    """Process and learn from spec book PDF with enhanced support"""
    try:
        spec_text = extract_text_from_pdf(file_content, use_ocr=use_ocr)
        if not spec_text:
            raise HTTPException(status_code=400, detail="No text extracted from spec PDF")
        
        chunks = chunk_text(spec_text)
        if not chunks:
            raise HTTPException(status_code=400, detail="No chunks created from spec text")
        
        logger.info(f"Generating embeddings for {len(chunks)} chunks...")
        
        # Optimize batch size based on available memory (smaller batches for free tier)
        batch_size = min(32, max(8, optimal_threads * 4))
        
        perf_monitor.start("Embeddings generation")
        embeddings = model.encode(
            chunks, 
            convert_to_tensor=False, 
            show_progress_bar=False,
            batch_size=batch_size,
            normalize_embeddings=True  # Normalize for better cosine similarity
        )
        perf_monitor.end("Embeddings generation")
        
        # Store embeddings
        os.makedirs(os.path.dirname(EMBEDDINGS_PATH) if os.path.dirname(EMBEDDINGS_PATH) else '.', exist_ok=True)
        with open(EMBEDDINGS_PATH, 'wb') as f:
            pickle.dump((chunks, embeddings), f)
        
        return {
            "message": "Spec book learned successfully",
            "chunks_learned": len(chunks),
            "storage_path": EMBEDDINGS_PATH
        }
    
    except HTTPException:
        raise  # Re-raise HTTP exceptions
    except Exception as e:
        logger.error(f"Error analyzing audit: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500, 
            detail="An error occurred while processing the PDF. Please ensure it's a valid audit document."
        )

def extract_go_back_infractions(text: str) -> List[str]:
    """Enhanced extraction with FuseSaver/Recloser keywords"""
    # Clean the text first
    text = clean_audit_garble(text)
    
    # Enhanced keywords for infractions
    keywords = [
        "go-back", "go back", "goback",
        "infraction", "violation", "issue",
        "non-compliance", "non-compliant", "noncompliant",
        "Rev. #", "Greenbook", "ampacity",
        "CIC", "fault", "QCInspection", "QC Inspection",
        "capacitors", "cutouts", "fuses",
        "disconnects", "risers", "sectionalizers",
        "reclosers", "line reclosers",
        "FuseSaver", "TripSaver",
        "SCADA", "SCADA-Mate", "SCADA-Mate SD",
        "bypass switches", "bypass switch",
        "incorrect", "improper", "missing",
        "not per spec", "deviation",
        "phasing", "rating", "coordination",
        "protection", "single-phase", "antenna"
    ]
    
    lines = text.split('\n')
    infractions = []
    
    for line in lines:
        if any(kw.lower() in line.lower() for kw in keywords):
            cleaned = re.sub(r'\s+', ' ', line.strip())
            if cleaned and len(cleaned) > 20:
                infractions.append(cleaned)
    
    # Deduplicate
    return list(set(infractions))

@app.get("/favicon.ico")
async def favicon():
    """Serve favicon"""
    favicon_path = os.path.join(static_dir, "favicon.ico") if 'static_dir' in locals() else "static/favicon.ico"
    if os.path.exists(favicon_path):
        return FileResponse(favicon_path)
    raise HTTPException(status_code=404, detail="Favicon not found")

@app.get("/")
async def root():
    """Root endpoint returning API info"""
    return {
        "name": "NEXA AI Document Analyzer",
        "version": "1.0.0 (October 2025 Enhanced)",
        "status": "healthy",
        "endpoints": [
            "/health",
            "/status",
            "/upload-spec-book",
            "/analyze-audit",
            "/docs"
        ],
        "features": [
            "FuseSaver support",
            "TripSaver support", 
            "SCADA-Mate SD support",
            "Line reclosers analysis",
            "Enhanced OCR cleaning",
            "1100MB file support"
        ]
    }

@app.get("/health", response_model=dict)
def health():
    """Health check endpoint"""
    spec_learned = os.path.exists(EMBEDDINGS_PATH)
    
    # Check OCR availability
    ocr_available = False
    try:
        pytesseract.get_tesseract_version()
        ocr_available = True
    except:
        pass
    
    return {
        "status": "healthy",
        "device": device,
        "spec_learned": spec_learned,
        "ocr_available": ocr_available,
        "max_file_size_mb": 1100
    }

@app.post("/upload-spec-book", response_model=SpecUploadResponse)
async def upload_spec_book(file: UploadFile = File(...)):
    """Upload and learn spec book PDF (max 1100MB)"""
    # Check file size
    content = await file.read()
    if len(content) > 1100 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="File too large (max 1100MB)")
    
    # Check file type
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")
    
    logger.info(f"Processing spec book: {file.filename}")
    result = learn_spec_book(content, use_ocr=True)
    return SpecUploadResponse(**result)

@app.get("/status")
async def get_status():
    """Check system status and spec book availability"""
    spec_ready = os.path.exists(EMBEDDINGS_PATH)
    spec_info = {}
    
    if spec_ready:
        try:
            with open(EMBEDDINGS_PATH, 'rb') as f:
                chunks, embeddings = pickle.load(f)
                spec_info = {
                    "chunks_loaded": len(chunks),
                    "ready": True,
                    "last_modified": time.ctime(os.path.getmtime(EMBEDDINGS_PATH))
                }
        except:
            spec_info = {"ready": False, "error": "Failed to load spec embeddings"}
    else:
        spec_info = {"ready": False, "message": "No spec book uploaded yet"}
    
    return {
        "status": "healthy",
        "version": "1.0.0 (October 2025 Enhanced)",
        "spec_book": spec_info,
        "cpu_threads": optimal_threads,
        "timestamp": time.time()
    }

@app.post("/analyze-audit", response_model=List[InfractionAnalysis])
async def analyze_audit(
    file: UploadFile = File(..., description="PDF file to analyze"),
    settings: Optional[str] = None  # JSON string for optional settings
):
    """Analyze audit PDF for infractions with enhanced matching
    
    Returns list of infraction analyses with confidence scores.
    Requires spec book to be uploaded first via /upload-spec-book endpoint.
    """
    # Parse optional settings
    request_settings = AuditAnalysisRequest()
    if settings:
        try:
            import json
            settings_dict = json.loads(settings)
            request_settings = AuditAnalysisRequest(**settings_dict)
        except Exception as e:
            logger.warning(f"Invalid settings provided: {e}")
    
    # Check spec book availability
    if not os.path.exists(EMBEDDINGS_PATH):
        raise HTTPException(
            status_code=400,
            detail="Spec book not learned yet. Please upload spec book first."
        )
    
    # Check file size
    content = await file.read()
    if len(content) > 1100 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="File too large (max 1100MB)")
    
    # Check file type
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")
    
    try:
        # Extract audit text
        logger.info(f"Extracting text from audit: {file.filename}")
        audit_text = extract_text_from_pdf(content, use_ocr=True)
        if not audit_text:
            raise HTTPException(status_code=400, detail="No text could be extracted from audit PDF")
        
        # Extract infractions
        infractions = extract_go_back_infractions(audit_text)
        logger.info(f"Found {len(infractions)} potential infractions")
        
        if not infractions:
            return []
        
        # Load spec embeddings
        with open(EMBEDDINGS_PATH, 'rb') as f:
            chunks, embeddings = pickle.load(f)
        
        # Analyze infractions with batch processing
        results = []
        confidence_threshold = request_settings.confidence_threshold
        max_infractions = min(request_settings.max_infractions, len(infractions))
        
        # Batch encode all infractions for better performance
        perf_monitor.start("Infraction embeddings")
        batch_size = min(32, max(8, optimal_threads * 4))
        inf_embeddings = model.encode(
            infractions[:max_infractions], 
            convert_to_tensor=False,
            batch_size=batch_size,
            normalize_embeddings=True
        )
        perf_monitor.end("Infraction embeddings")
        
        # Process each infraction with its pre-computed embedding
        perf_monitor.start("Similarity matching")
        for idx, inf in enumerate(infractions[:max_infractions]):
            # Use pre-computed embedding
            inf_emb = inf_embeddings[idx:idx+1]
            
            # Calculate cosine similarity (optimized with normalized vectors)
            cos_scores = util.cos_sim(inf_emb, embeddings)[0]
            
            # Get top matches
            top_k = 5
            top_idx = cos_scores.argsort(descending=True)[:top_k]
            top_scores = cos_scores[top_idx]
            
            # Filter by threshold
            relevant = []
            for idx, score in zip(top_idx, top_scores):
                if score.item() > confidence_threshold:
                    relevant.append((chunks[idx], score.item()))
            
            match_count = len(relevant)
            avg_score = sum(score for _, score in relevant) / len(relevant) if relevant else 0
            confidence = avg_score * 100
            
            # Enhanced decision logic for FuseSaver/Recloser specs
            is_repealable = False
            reasons = []
            
            # Check for specific equipment matches
            equipment_keywords = ['FuseSaver', 'TripSaver', 'recloser', 'SCADA']
            has_equipment_match = any(kw.lower() in inf.lower() for kw in equipment_keywords)
            
            if match_count >= 2 and confidence > 60:
                is_repealable = True
                
                # If equipment-specific, boost confidence
                if has_equipment_match and confidence > 70:
                    confidence = min(confidence * 1.1, 100.0)
            
            # Generate reasons
            for chunk, score in relevant[:3]:
                # Identify source document if possible
                doc_match = re.search(r'Document (\d+|TD-\d+P-\d+)', chunk)
                doc_ref = doc_match.group(0) if doc_match else "Spec"
                
                # Check for specific notes
                if 'single-phase' in chunk.lower() and 'FuseSaver' in inf:
                    reasons.append(f"From {doc_ref}: FuseSavers must be installed on single phase taps only (similarity {score:.0%})")
                elif 'rating' in chunk.lower() and 'recloser' in inf.lower():
                    reasons.append(f"From {doc_ref}: Recloser ratings must match spec requirements (similarity {score:.0%})")
                elif 'SCADA' in chunk and 'antenna' in inf.lower():
                    reasons.append(f"From {doc_ref}: SCADA antenna installation requirements (similarity {score:.0%})")
                else:
                    chunk_preview = chunk[:150]
                    reasons.append(f"{doc_ref} match (similarity {score:.0%}): {chunk_preview}...")
            
            if not reasons:
                reasons = ["No strong spec matches found - infraction appears valid"]
            
            results.append(InfractionAnalysis(
                infraction=inf[:200] + "..." if len(inf) > 200 else inf,
                status="REPEALABLE" if is_repealable else "VALID",
                confidence=round(confidence, 1),
                match_count=match_count,
                reasons=reasons
            ))
        
        perf_monitor.end("Similarity matching")
        
        logger.info(f"Analysis complete: {len(results)} infractions processed")
        return results
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Analysis failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
