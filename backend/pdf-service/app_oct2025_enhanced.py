"""
NEXA AI Document Analyzer - Multi-Spec Support
Enhanced version with multiple spec file support and persistent storage
"""
import os
import io
import pickle
import json
from datetime import datetime
from contextlib import asynccontextmanager
from fastapi import FastAPI, File, UploadFile, HTTPException, Depends, Query, Form
from fastapi.responses import JSONResponse
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
from functools import lru_cache  # Week 1: Added for caching spec lookups
from middleware import ValidationMiddleware, ErrorHandlingMiddleware, RateLimitMiddleware
import hashlib

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Computer Vision for pole detection (if available)
try:
    from modules.vision_endpoints import vision_router
    VISION_ENABLED = True
    logger.info("Vision detection enabled with Roboflow model")
except ImportError as e:
    VISION_ENABLED = False
    logger.warning(f"Vision detection not available: {e}")
    vision_router = None

# Pricing integration for cost impact analysis
try:
    from modules.pricing_endpoints import pricing_router, init_pricing_analyzer
    from modules.pricing_integration import enhance_infraction_with_pricing, PricingAnalyzer
    PRICING_ENABLED = True
    logger.info("💰 Pricing integration enabled")
except ImportError as e:
    PRICING_ENABLED = False
    logger.warning(f"Pricing integration not available: {e}")
    pricing_router = None

# Job Package Training integration
try:
    from modules.job_package_training_api import add_training_endpoints
    TRAINING_ENABLED = True
    logger.info("📚 Job package training enabled - NEXA can learn to fill packages!")
except ImportError as e:
    TRAINING_ENABLED = False
    logger.warning(f"Job package training not available: {e}")
    add_training_endpoints = None

# Enhanced Spec Analyzer with Fine-Tuned NER
try:
    from modules.enhanced_spec_analyzer import integrate_with_app as add_enhanced_analyzer
    ENHANCED_ANALYZER_ENABLED = True
    logger.info("🎯 Enhanced analyzer with poles/underground NER enabled!")
except ImportError as e:
    ENHANCED_ANALYZER_ENABLED = False
    logger.warning(f"Enhanced analyzer not available: {e}")
    add_enhanced_analyzer = None

# Spec Learning System
try:
    from modules.spec_learning_endpoints import integrate_spec_learning
    SPEC_LEARNING_ENABLED = True
    logger.info("📚 Spec learning system enabled - Upload PG&E PDFs!")
except ImportError as e:
    SPEC_LEARNING_ENABLED = False
    logger.warning(f"Spec learning not available: {e}")
    integrate_spec_learning = None

# === CPU PERFORMANCE OPTIMIZATION ===
num_cores = int(os.environ.get('RENDER_CORES', len(os.sched_getaffinity(0)) if hasattr(os, 'sched_getaffinity') else cpu_count()))
optimal_threads = max(1, num_cores // 2)

torch.set_num_threads(optimal_threads)
torch.set_num_interop_threads(1)

os.environ.setdefault('OMP_NUM_THREADS', str(optimal_threads))
os.environ.setdefault('MKL_NUM_THREADS', str(optimal_threads))
os.environ.setdefault('PYTORCH_ENABLE_MPS_FALLBACK', '1')

# Download NLTK data
nltk.download('punkt', quiet=True)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Modern lifespan handler for startup and shutdown events"""
    # Startup code
    logger.info("Starting NEXA Field Management System...")
    
    # Pre-load vision model if enabled
    if VISION_ENABLED:
        try:
            # Check for Roboflow API key
            if not os.getenv('ROBOFLOW_API_KEY'):
                logger.warning("ROBOFLOW_API_KEY not set - vision will use base YOLOv8")
            else:
                logger.info("Roboflow API key found, will download utility-pole-detection-birhf model")
            
            # Pre-initialize detector to download model
            from modules.pole_vision_detector import PoleVisionDetector
            detector = PoleVisionDetector()
            logger.info("Vision model pre-loaded successfully")
            
            # Test model status
            if os.path.exists('/data/yolo_pole.pt'):
                logger.info("✅ Roboflow model ready at /data/yolo_pole.pt")
            else:
                logger.info("⏳ Model will download on first use")
                
        except Exception as e:
            logger.error(f"Could not pre-load vision model: {e}")
    
    # Check for fine-tuned NER model
    ner_model_path = '/data/fine_tuned_ner_deep'
    if os.path.exists(ner_model_path):
        try:
            # Load fine-tuned NER with F1=0.87
            from transformers import AutoModelForTokenClassification, AutoTokenizer, pipeline
            ner_model = AutoModelForTokenClassification.from_pretrained(ner_model_path)
            ner_tokenizer = AutoTokenizer.from_pretrained(ner_model_path)
            
            # Create NER pipeline for easy inference
            ner_pipeline = pipeline(
                "token-classification",
                model=ner_model,
                tokenizer=ner_tokenizer,
                aggregation_strategy="simple"
            )
            
            logger.info("✅ Fine-tuned NER model loaded (F1=0.87) from /data/fine_tuned_ner_deep")
            NER_AVAILABLE = True
        except Exception as e:
            logger.warning(f"Could not load fine-tuned NER: {e}")
            NER_AVAILABLE = False
            ner_pipeline = None
    else:
        logger.warning("Fine-tuned NER model not found - using pattern fallback")
        NER_AVAILABLE = False
        ner_pipeline = None
    
    # Initialize pricing if enabled
    if PRICING_ENABLED:
        try:
            init_pricing_analyzer(app)
            logger.info("💰 Pricing analyzer initialized")
        except Exception as e:
            logger.warning(f"Pricing analyzer initialization failed: {e}")
    
    yield  # Server is running
    
    # Shutdown code
    logger.info("Shutting down NEXA Field Management System...")

app = FastAPI(
    title="NEXA Universal Standards Platform",
    description="AI-powered universal utility standards analyzer",
    version="3.0"
)
# Add middleware - ORDER MATTERS! CORS must be last
app.add_middleware(RateLimitMiddleware, calls=200, period=60)  # Week 1: Increased for 30 users
app.add_middleware(ErrorHandlingMiddleware)
app.add_middleware(ValidationMiddleware)

# CORS middleware MUST be added last to process responses correctly
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"]
)

# Model setup
device = 'cpu'
logger.info(f"🔧 Using device: {device}")
model = SentenceTransformer('all-MiniLM-L6-v2', device=device)

# Persistence paths - ALWAYS use /data on Render
DATA_PATH = '/data'
EMBEDDINGS_PATH = os.path.join(DATA_PATH, 'spec_embeddings.pkl')
SPEC_METADATA_PATH = os.path.join(DATA_PATH, 'spec_metadata.json')

# Create data directory if it doesn't exist
os.makedirs(DATA_PATH, exist_ok=True)

logger.info(f"💾 Data storage path: {DATA_PATH}")

# Initialize pricing analyzer if available
pricing_analyzer = None
if PRICING_ENABLED:
    pricing_analyzer = init_pricing_analyzer(model, DATA_PATH)
    logger.info("💰 Pricing analyzer initialized")

# Include vision router if available
if VISION_ENABLED and vision_router:
    app.include_router(vision_router)
    logger.info("Vision endpoints registered at /vision/*")

# Include pricing router if available
if PRICING_ENABLED and pricing_router:
    app.include_router(pricing_router, prefix="/pricing", tags=["Pricing"])
    logger.info("💰 Pricing endpoints registered at /pricing/*")

# Include training endpoints if available
if TRAINING_ENABLED and add_training_endpoints:
    add_training_endpoints(app)
    logger.info("📚 Training endpoints registered - /train-job-package, /train-as-built, /batch-train-packages")

# Include enhanced analyzer if available
if ENHANCED_ANALYZER_ENABLED and add_enhanced_analyzer:
    add_enhanced_analyzer(app)
    logger.info("🎯 Enhanced analyzer endpoints registered - /analyze-go-back, /batch-analyze-go-backs")

# Include spec learning system if available
if SPEC_LEARNING_ENABLED and integrate_spec_learning:
    integrate_spec_learning(app)
    logger.info("📚 Spec learning endpoints registered - /spec-learning/learn-spec, /spec-learning/search-specs")

# Mega Bundle Analysis System
try:
    from modules.mega_bundle_endpoints import integrate_mega_bundle_endpoints
    MEGA_BUNDLE_ENABLED = True
    logger.info("📦 Mega bundle analysis enabled - Process 3500+ jobs!")
except ImportError as e:
    MEGA_BUNDLE_ENABLED = False
    logger.warning(f"Mega bundle analysis not available: {e}")
    integrate_mega_bundle_endpoints = None

if MEGA_BUNDLE_ENABLED and integrate_mega_bundle_endpoints:
    integrate_mega_bundle_endpoints(app)
    logger.info("✅ Mega bundle endpoints registered - /mega-bundle/upload, /mega-bundle/status")

# Spec-Based Hour Estimation System
try:
    from modules.spec_based_hour_estimator import integrate_spec_hour_estimation
    HOUR_ESTIMATION_ENABLED = True
    logger.info("⏰ Spec-based hour estimation enabled - More accurate profitability!")
except ImportError as e:
    HOUR_ESTIMATION_ENABLED = False
    logger.warning(f"Hour estimation not available: {e}")
    integrate_spec_hour_estimation = None

if HOUR_ESTIMATION_ENABLED and integrate_spec_hour_estimation:
    integrate_spec_hour_estimation(app)
    logger.info("✅ Hour estimation endpoints registered - /hour-estimation/estimate")

# Model Fine-Tuning System
try:
    from modules.model_fine_tuner import integrate_fine_tuning_endpoints
    FINE_TUNING_ENABLED = True
    logger.info("🎯 Model fine-tuning enabled - Improve NER/YOLO/embeddings!")
except ImportError as e:
    FINE_TUNING_ENABLED = False
    logger.warning(f"Fine-tuning not available: {e}")
    integrate_fine_tuning_endpoints = None

if FINE_TUNING_ENABLED and integrate_fine_tuning_endpoints:
    integrate_fine_tuning_endpoints(app)
    logger.info("✅ Fine-tuning endpoints registered - /fine-tune/start, /fine-tune/progress")

# Conduit NER Fine-Tuning System
try:
    from modules.conduit_ner_fine_tuner import integrate_conduit_ner_endpoints
    CONDUIT_NER_ENABLED = True
    logger.info("🚇 Conduit NER fine-tuning enabled - Improve underground analysis!")
except ImportError as e:
    CONDUIT_NER_ENABLED = False
    logger.warning(f"Conduit NER fine-tuning not available: {e}")
    integrate_conduit_ner_endpoints = None

if CONDUIT_NER_ENABLED and integrate_conduit_ner_endpoints:
    integrate_conduit_ner_endpoints(app)
    logger.info("✅ Conduit NER endpoints registered - /fine-tune-conduits/start")

# Enhanced Conduit Analyzer
try:
    from modules.conduit_enhanced_analyzer import integrate_enhanced_analyzer
    CONDUIT_ANALYZER_ENABLED = True
    logger.info("🔍 Enhanced conduit analyzer enabled - >90% go-back confidence!")
except ImportError as e:
    CONDUIT_ANALYZER_ENABLED = False
    logger.warning(f"Enhanced conduit analyzer not available: {e}")
    integrate_enhanced_analyzer = None

if CONDUIT_ANALYZER_ENABLED and integrate_enhanced_analyzer:
    integrate_enhanced_analyzer(app)
    logger.info("✅ Conduit analyzer endpoints registered - /conduit-analysis/*")

# Overhead Lines NER Fine-Tuning System
try:
    from modules.overhead_ner_fine_tuner import integrate_overhead_ner_endpoints
    OVERHEAD_NER_ENABLED = True
    logger.info("⚡ Overhead NER fine-tuning enabled - Improve conductor/insulator analysis!")
except ImportError as e:
    OVERHEAD_NER_ENABLED = False
    logger.warning(f"Overhead NER fine-tuning not available: {e}")
    integrate_overhead_ner_endpoints = None

if OVERHEAD_NER_ENABLED and integrate_overhead_ner_endpoints:
    integrate_overhead_ner_endpoints(app)
    logger.info("✅ Overhead NER endpoints registered - /fine-tune-overhead/*")

# Enhanced Overhead Analyzer
try:
    from modules.overhead_enhanced_analyzer import integrate_overhead_analyzer
    OVERHEAD_ANALYZER_ENABLED = True
    logger.info("📡 Enhanced overhead analyzer enabled - >85% go-back confidence!")
except ImportError as e:
    OVERHEAD_ANALYZER_ENABLED = False
    logger.warning(f"Enhanced overhead analyzer not available: {e}")
    integrate_overhead_analyzer = None

if OVERHEAD_ANALYZER_ENABLED and integrate_overhead_analyzer:
    integrate_overhead_analyzer(app)
    logger.info("✅ Overhead analyzer endpoints registered - /overhead-analysis/*")

# Clearance-Enhanced NER Fine-Tuning System  
try:
    from modules.clearance_enhanced_fine_tuner import integrate_clearance_fine_tuning_endpoints
    CLEARANCE_FINETUNE_ENABLED = True
    logger.info("🚂 Clearance NER fine-tuning enabled - Target F1 >0.9!")
except ImportError as e:
    CLEARANCE_FINETUNE_ENABLED = False
    logger.warning(f"Clearance fine-tuning not available: {e}")
    integrate_clearance_fine_tuning_endpoints = None

if CLEARANCE_FINETUNE_ENABLED and integrate_clearance_fine_tuning_endpoints:
    integrate_clearance_fine_tuning_endpoints(app)
    logger.info("✅ Clearance fine-tuning endpoints registered - /fine-tune-clearances/*")

# Clearance Analyzer
try:
    from modules.clearance_analyzer import integrate_clearance_analyzer
    CLEARANCE_ANALYZER_ENABLED = True
    logger.info("📏 Clearance analyzer enabled - Railroad/ground clearance analysis!")
except ImportError as e:
    CLEARANCE_ANALYZER_ENABLED = False
    logger.warning(f"Clearance analyzer not available: {e}")
    integrate_clearance_analyzer = None

if CLEARANCE_ANALYZER_ENABLED and integrate_clearance_analyzer:
    integrate_clearance_analyzer(app)
    logger.info("✅ Clearance analyzer endpoints registered - /clearance-analysis/*")

# Universal Standards Engine
try:
    from modules.universal_standards import integrate_universal_endpoints
    UNIVERSAL_STANDARDS_ENABLED = True
    logger.info("🌍 Universal Standards Engine enabled - Multi-utility support!")
except ImportError as e:
    UNIVERSAL_STANDARDS_ENABLED = False
    logger.warning(f"Universal Standards Engine not available: {e}")
    integrate_universal_endpoints = None

if UNIVERSAL_STANDARDS_ENABLED and integrate_universal_endpoints:
    integrate_universal_endpoints(app)
    logger.info("✅ Universal Standards endpoints registered - /api/utilities/*")

# Authentication System
try:
    from modules.auth_system import integrate_auth, get_current_user
    AUTH_ENABLED = True
    logger.info("🔐 Authentication system enabled")
except ImportError as e:
    AUTH_ENABLED = False
    logger.warning(f"Authentication system not available: {e}")
    integrate_auth = None
    get_current_user = None

if AUTH_ENABLED and integrate_auth:
    integrate_auth(app)
    logger.info("✅ Authentication endpoints registered - /auth/*")

# Roboflow Dataset Integration
try:
    from modules.roboflow_dataset_integrator import integrate_roboflow_datasets
    ROBOFLOW_ENABLED = True
    logger.info("🖼️ Roboflow integration enabled - Fix crossarm detection!")
except ImportError as e:
    ROBOFLOW_ENABLED = False
    logger.warning(f"Roboflow integration not available: {e}")
    integrate_roboflow_datasets = None

if ROBOFLOW_ENABLED and integrate_roboflow_datasets:
    integrate_roboflow_datasets(app)
    logger.info("✅ Roboflow endpoints registered - /roboflow/download-datasets, /roboflow/merge-and-train")

# === MODELS ===
class SpecFile(BaseModel):
    """Information about an uploaded spec file"""
    filename: str
    upload_time: str
    chunk_count: int
    file_hash: str
    file_size: int

class SpecLibrary(BaseModel):
    """Current spec library status"""
    total_files: int
    total_chunks: int
    files: List[SpecFile]
    last_updated: Optional[str]
    storage_path: str

class MultiSpecUploadResponse(BaseModel):
    """Response for multi-spec upload"""
    message: str
    files_processed: int
    total_chunks: int
    new_chunks_added: int
    library_status: SpecLibrary

class SpecManagementRequest(BaseModel):
    """Request for spec management operations"""
    operation: str = Field(..., pattern='^(clear|remove|list)$')
    file_hash: Optional[str] = Field(None, description="File hash for remove operation")

# === HELPER FUNCTIONS ===
def get_file_hash(content: bytes) -> str:
    """Generate SHA256 hash of file content"""
    return hashlib.sha256(content).hexdigest()[:16]

def load_spec_library() -> Dict[str, Any]:
    """Load existing spec library with metadata"""
    # Default structure with all required fields
    library = {
        'chunks': [],
        'embeddings': [],
        'metadata': {
            'files': [],
            'total_chunks': 0,
            'last_updated': None
        }
    }
    
    # Load embeddings if they exist
    if os.path.exists(EMBEDDINGS_PATH):
        try:
            with open(EMBEDDINGS_PATH, 'rb') as f:
                data = pickle.load(f)
                # Handle different formats
                if isinstance(data, tuple) and len(data) == 2:
                    chunks, embeddings = data
                    library['chunks'] = chunks if isinstance(chunks, list) else []
                    library['embeddings'] = embeddings if hasattr(embeddings, '__len__') else []
                elif isinstance(data, dict):
                    # Merge with default structure to ensure all keys exist
                    if 'chunks' in data:
                        library['chunks'] = data['chunks']
                    if 'embeddings' in data:
                        library['embeddings'] = data['embeddings']
                    if 'metadata' in data and isinstance(data['metadata'], dict):
                        # Ensure metadata has all required fields
                        library['metadata'].update(data['metadata'])
                        if 'files' not in library['metadata']:
                            library['metadata']['files'] = []
                else:
                    logger.warning(f"Unknown embeddings format: {type(data)}")
        except Exception as e:
            logger.warning(f"Could not load embeddings: {e}")
    
    # Load metadata if it exists
    if os.path.exists(SPEC_METADATA_PATH):
        try:
            with open(SPEC_METADATA_PATH, 'r') as f:
                metadata = json.load(f)
                # Ensure metadata has all required fields
                if isinstance(metadata, dict):
                    if 'files' not in metadata:
                        metadata['files'] = []
                    # Convert float timestamps to ISO strings for backward compatibility
                    for file_info in metadata.get('files', []):
                        if isinstance(file_info.get('upload_time'), (int, float)):
                            file_info['upload_time'] = datetime.fromtimestamp(file_info['upload_time']).isoformat()
                    if isinstance(metadata.get('last_updated'), (int, float)):
                        metadata['last_updated'] = datetime.fromtimestamp(metadata['last_updated']).isoformat()
                    library['metadata'].update(metadata)
        except Exception as e:
            logger.warning(f"Could not load metadata: {e}")
    
    # Ensure metadata always has required fields
    if 'files' not in library['metadata']:
        library['metadata']['files'] = []
    if 'total_chunks' not in library['metadata']:
        library['metadata']['total_chunks'] = len(library.get('chunks', []))
    
    # Initialize with default spec if empty (for testing)
    if len(library['chunks']) == 0:
        logger.info("🎯 Initializing with default PG&E spec sample for testing")
        default_chunks = [
            "PG&E Document 045786: Capacitor spacing shall be 36 inches minimum in urban zones.",
            "PG&E Document 035986: Single-phase taps require FuseSaver protection devices.",
            "PG&E Document 072136: Pole top clearance must maintain 12 feet from energized conductors.",
            "Overhead line clearances per GO-95 Rule 35: 18 feet minimum over roadways.",
            "Underground conduit specifications: 4-inch minimum for primary voltage."
        ]
        library['chunks'] = default_chunks
        # Generate mock embeddings using the global model
        library['embeddings'] = model.encode(default_chunks, convert_to_tensor=False)
        library['metadata']['files'] = [{
            'filename': 'default_pge_spec.pdf',
            'upload_time': datetime.now().isoformat(),
            'file_hash': 'default_mock_spec',
            'chunk_count': len(default_chunks),
            'file_size': 1000
        }]
        library['metadata']['total_chunks'] = len(default_chunks)
        logger.info(f"✅ Loaded {len(default_chunks)} default spec chunks")
    
    return library

def save_spec_library(library: Dict[str, Any]):
    """Save spec library with metadata"""
    # Create directory if needed
    os.makedirs(DATA_PATH, exist_ok=True)
    
    # Ensure embeddings are in list format for saving
    embeddings = library['embeddings']
    if hasattr(embeddings, 'tolist'):
        embeddings = embeddings.tolist()
    
    # Save embeddings
    with open(EMBEDDINGS_PATH, 'wb') as f:
        pickle.dump((library['chunks'], embeddings), f)
    
    # Update metadata
    library['metadata']['total_chunks'] = len(library['chunks'])
    library['metadata']['last_updated'] = datetime.utcnow().isoformat()
    
    # Save metadata
    with open(SPEC_METADATA_PATH, 'w') as f:
        json.dump(library['metadata'], f, indent=2)

def extract_text_chunks(pdf_content: bytes, filename: str, chunk_size: int = 400) -> List[str]:
    """Extract and chunk text from PDF with OCR cleaning - Week 1: Optimized chunk size"""
    try:
        pdf_reader = PdfReader(io.BytesIO(pdf_content))
        chunks = []
        
        for page_num, page in enumerate(pdf_reader.pages):
            text = page.extract_text()
            if text:
                # Clean the text
                cleaned_text = clean_audit_garble(text)
                
                # Split into chunks
                words = cleaned_text.split()
                current_chunk = []
                current_length = 0
                
                for word in words:
                    word_length = len(word) + 1  # +1 for space
                    if current_length + word_length > chunk_size and current_chunk:
                        chunk_text = ' '.join(current_chunk)
                        chunks.append(f"[{filename} p.{page_num+1}] {chunk_text}")
                        current_chunk = [word]
                        current_length = word_length
                    else:
                        current_chunk.append(word)
                        current_length += word_length
                
                # Add remaining words as final chunk
                if current_chunk:
                    chunk_text = ' '.join(current_chunk)
                    chunks.append(f"[{filename} p.{page_num+1}] {chunk_text}")
        
        logger.info(f"📄 Extracted {len(chunks)} chunks from {filename}")
        return chunks
        
    except Exception as e:
        logger.error(f"Error extracting text from {filename}: {e}")
        return []

def clean_audit_garble(text: str) -> str:
    """Enhanced cleaning for audit text garble"""
    original_length = len(text)
    
    # Fix common OCR issues
    text = re.sub(r'andentercallsnotlistedatendofeachsection\.\)No', '', text)
    text = re.sub(r'(\w)\s+(\w)', r'\1\2', text)  # Fix split words
    text = re.sub(r'\s+', ' ', text)  # Normalize spaces
    text = re.sub(r'\)\.?No', '', text)  # Remove common audit endings
    
    # More aggressive cleaning
    text = re.sub(r'QCInspectionandentercalls', 'QC Inspection and enter calls', text)
    text = re.sub(r'notlistedatendofeachsection', 'not listed at end of each section', text)
    
    if original_length != len(text):
        logger.info(f"🧹 Cleaned audit text: reduced from {original_length} to {len(text)} chars")
    
    return text.strip()

def extract_text_from_pdf(pdf_content: bytes, use_ocr: bool = False) -> str:
    """Extract text from PDF with optional OCR support"""
    try:
        pdf = PdfReader(io.BytesIO(pdf_content))
        text = ""
        ocr_pages = 0
        
        for i, page in enumerate(pdf.pages):
            page_text = page.extract_text() or ""
            
            # Clean the extracted text
            page_text = clean_audit_garble(page_text)
            
            # Use OCR if text extraction is poor
            if use_ocr and len(page_text.strip()) < 100:
                try:
                    # Convert PDF page to image for OCR
                    # Note: This requires pdf2image which needs poppler
                    from pdf2image import convert_from_bytes
                    images = convert_from_bytes(pdf_content, first_page=i+1, last_page=i+1)
                    if images:
                        ocr_text = pytesseract.image_to_string(images[0])
                        if len(ocr_text) > len(page_text):
                            page_text = ocr_text
                            ocr_pages += 1
                            logger.info(f"OCR extracted text from page {i+1}")
                except Exception as e:
                    logger.debug(f"OCR failed for page {i+1}: {e}")
            
            text += page_text + "\n"
        
        # Final cleanup
        text = clean_audit_garble(text)
        
        if ocr_pages > 0:
            logger.info(f"OCR was used on {ocr_pages} pages")
        
        return text
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to extract text: {str(e)}")

def chunk_text(text: str, chunk_size: int = 1100) -> List[str]:
    """Split text into chunks for embedding"""
    sentences = nltk.sent_tokenize(text)
    chunks = []
    current = ''
    
    for sentence in sentences:
        if len(current) + len(sentence) > chunk_size:
            if current.strip():
                chunks.append(current.strip())
            current = sentence
        else:
            current += ' ' + sentence
    
    if current.strip():
        chunks.append(current.strip())
    
    return chunks

def process_spec_file(file_content: bytes, filename: str, use_ocr: bool = False) -> Dict[str, Any]:
    """Process a single spec file and return chunks and metadata"""
    # Extract text
    spec_text = extract_text_from_pdf(file_content, use_ocr=use_ocr)
    if not spec_text:
        raise ValueError(f"No text extracted from {filename}")
    
    # Create chunks
    chunks = chunk_text(spec_text)
    if not chunks:
        raise ValueError(f"No chunks created from {filename}")
    
    # Tag chunks with source file
    tagged_chunks = [f"[Source: {filename}] {chunk}" for chunk in chunks]
    
    # Generate embeddings
    batch_size = min(32, max(8, optimal_threads * 4))
    embeddings = model.encode(
        tagged_chunks,
        convert_to_tensor=False,
        show_progress_bar=False,
        batch_size=batch_size,
        normalize_embeddings=True
    )
    
    # Create metadata
    file_hash = get_file_hash(file_content)
    metadata = SpecFile(
        filename=filename,
        upload_time=datetime.utcnow().isoformat(),
        chunk_count=len(chunks),
        file_hash=file_hash,
        file_size=len(file_content)
    )
    
    return {
        'chunks': tagged_chunks,
        'embeddings': embeddings,
        'metadata': metadata
    }

# === API ENDPOINTS ===

@app.get("/")
async def root():
    """Root endpoint with API info"""
    return {
        "name": "NEXA AI Document Analyzer - Multi-Spec",
        "version": "2.0.0",
        "status": "healthy",
        "endpoints": [
            "/health",
            "/status",
            "/spec-library",
            "/upload-specs",
            "/manage-specs",
            "/analyze-audit",
            "/docs"
        ],
        "features": [
            "Multiple spec file support",
            "Persistent spec storage",
            "Spec library management",
            "Source tracking for matches",
            "Incremental learning"
        ]
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": time.time()}

@app.get("/status")
async def status():
    """Comprehensive system status endpoint"""
    try:
        # Check model status
        model_loaded = model is not None
        
        # Check spec library
        spec_loaded = False
        total_specs = 0
        if os.path.exists(SPEC_METADATA_PATH):
            try:
                with open(SPEC_METADATA_PATH, 'r') as f:
                    metadata = json.load(f)
                    total_specs = len(metadata.get('specs', []))
                    spec_loaded = total_specs > 0
            except:
                pass
        
        # Check feature availability
        features = {
            "vision": VISION_ENABLED,
            "pricing": PRICING_ENABLED,
            "training": TRAINING_ENABLED,
            "enhanced_analyzer": ENHANCED_ANALYZER_ENABLED,
            "spec_learning": SPEC_LEARNING_ENABLED,
            "mega_bundle": MEGA_BUNDLE_ENABLED,
            "hour_estimation": HOUR_ESTIMATION_ENABLED,
            "fine_tuning": FINE_TUNING_ENABLED,
            "conduit_ner": CONDUIT_NER_ENABLED
        }
        
        # System info
        return {
            "status": "operational",
            "model_loaded": model_loaded,
            "spec_loaded": spec_loaded,
            "total_specs": total_specs,
            "features_enabled": features,
            "data_path": DATA_PATH,
            "device": device,
            "embeddings_exist": os.path.exists(EMBEDDINGS_PATH),
            "timestamp": datetime.now().isoformat(),
            "version": "oct2025_enhanced",
            "cpu_cores": num_cores,
            "torch_threads": optimal_threads
        }
    except Exception as e:
        logger.error(f"Error in /status endpoint: {e}")
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

@app.get("/spec-library", response_model=SpecLibrary)
async def get_spec_library():
    """Get current spec library status"""
    try:
        library = load_spec_library()
        
        # Ensure all required fields exist
        metadata = library.get('metadata', {})
        files = metadata.get('files', [])
        chunks = library.get('chunks', [])
        
        return SpecLibrary(
            total_files=len(files),
            total_chunks=len(chunks),
            files=files,
            last_updated=metadata.get('last_updated'),
            storage_path=DATA_PATH
        )
    except Exception as e:
        logger.error(f"Error loading spec library: {e}")
        # Return empty library on error
        return SpecLibrary(
            total_files=0,
            total_chunks=0,
            files=[],
            last_updated=None,
            storage_path=DATA_PATH
        )

@app.post("/learn-spec/")
async def learn_single_spec(file: UploadFile = File(...)):
    """Upload and learn a single spec PDF (convenience endpoint)"""
    try:
        mode = "append"
        
        # Validate file
        if not file.filename.lower().endswith('.pdf'):
            raise HTTPException(status_code=400, detail="Only PDF files are allowed")
        
        # Read file content
        content = await file.read()
        file_size = len(content)
        
        if file_size > 1100 * 1024 * 1024:  # 1100MB limit
            raise HTTPException(status_code=400, detail="File too large (max 1100MB)")
        
        # Process the single file
        start_time = time.time()
        library = load_spec_library()
        
        if mode == 'replace':
            library = {'chunks': [], 'embeddings': [], 'metadata': {'files': [], 'last_updated': None}}
        
        # Get file hash for deduplication
        file_hash = get_file_hash(content)
        existing_hashes = {f.get('file_hash') for f in library.get('metadata', {}).get('files', [])}
        
        if file_hash in existing_hashes:
            raise HTTPException(status_code=400, detail=f"File already uploaded: {file.filename}")
        
        # Extract and process chunks
        chunks = extract_text_chunks(content, file.filename)
        
        if not chunks:
            raise HTTPException(status_code=400, detail="No text could be extracted from PDF")
        
        # Generate embeddings
        logger.info(f"Generating embeddings for {len(chunks)} chunks...")
        embed_start = time.time()
        new_embeddings = model.encode(chunks, normalize_embeddings=True, show_progress_bar=False)
        logger.info(f"⏱️ Embeddings generation: {time.time() - embed_start:.2f}s")
        
        # Add to library - handle both list and numpy array formats
        library['chunks'].extend(chunks)
        
        # Convert embeddings to list if they're numpy arrays
        if hasattr(library['embeddings'], 'tolist'):
            library['embeddings'] = library['embeddings'].tolist()
        if not isinstance(library['embeddings'], list):
            library['embeddings'] = []
            
        # Add new embeddings
        if hasattr(new_embeddings, 'tolist'):
            library['embeddings'].extend(new_embeddings.tolist())
        else:
            library['embeddings'].extend(new_embeddings)
        
        # Update metadata - ensure it exists and has correct structure
        if 'metadata' not in library or library['metadata'] is None:
            library['metadata'] = {'files': [], 'last_updated': None}
        
        if 'files' not in library['metadata']:
            library['metadata']['files'] = []
        
        library['metadata']['files'].append({
            'filename': file.filename,
            'file_hash': file_hash,
            'chunk_count': len(chunks),
            'file_size': file_size,
            'upload_time': datetime.utcnow().isoformat()
        })
        library['metadata']['last_updated'] = datetime.utcnow().isoformat()
        
        # Save library
        save_spec_library(library)
        
        processing_time = time.time() - start_time
        logger.info(f"✅ Spec learned successfully: {file.filename} ({len(chunks)} chunks in {processing_time:.2f}s)")
        
        return {
            "message": "Spec book learned successfully",
            "chunks_learned": len(chunks),
            "storage_path": str(DATA_PATH)
        }
    
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Error in /learn-spec/: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.post("/upload-specs", response_model=MultiSpecUploadResponse)
async def upload_multiple_specs(
    files: List[UploadFile] = File(..., description="PDF spec files to upload"),
    mode: str = Form(default="append", description="append or replace")
):
    """
    Upload multiple spec files at once
    
    Modes:
    - append: Add to existing spec library (default)
    - replace: Replace entire spec library
    """
    if mode not in ['append', 'replace']:
        raise HTTPException(status_code=400, detail="Mode must be 'append' or 'replace'")
    
    # Validate files
    for file in files:
        if not file.filename.lower().endswith('.pdf'):
            raise HTTPException(
                status_code=400, 
                detail=f"File {file.filename} is not a PDF"
            )
    
    # Load existing library or create new
    if mode == 'append':
        library = load_spec_library()
    else:
        library = {
            'chunks': [],
            'embeddings': [],
            'metadata': {'files': [], 'total_chunks': 0}
        }
    
    # Process each file
    processed_files = 0
    new_chunks_added = 0
    errors = []
    
    for file in files:
        try:
            logger.info(f"Processing spec file: {file.filename}")
            
            # Read file content
            content = await file.read()
            if len(content) > 100 * 1024 * 1024:  # 100MB per file limit
                errors.append(f"{file.filename}: File too large (max 100MB)")
                continue
            
            # Check if file already exists (by hash)
            file_hash = get_file_hash(content)
            existing_hashes = [f.file_hash for f in library['metadata'].get('files', [])]
            
            if file_hash in existing_hashes:
                logger.info(f"Skipping {file.filename} - already in library")
                continue
            
            # Process the file
            result = process_spec_file(content, file.filename, use_ocr=True)
            
            # Add to library
            library['chunks'].extend(result['chunks'])
            
            # Handle embeddings (numpy array or list)
            if len(library['embeddings']) == 0:
                library['embeddings'] = result['embeddings']
            else:
                import numpy as np
                library['embeddings'] = np.vstack([library['embeddings'], result['embeddings']])
            
            # Add metadata
            library['metadata']['files'].append(result['metadata'].dict())
            
            processed_files += 1
            new_chunks_added += len(result['chunks'])
            
        except Exception as e:
            logger.error(f"Error processing {file.filename}: {e}")
            errors.append(f"{file.filename}: {str(e)}")
    
    if processed_files == 0 and errors:
        raise HTTPException(
            status_code=400,
            detail=f"No files processed successfully. Errors: {'; '.join(errors)}"
        )
    
    # Save updated library
    save_spec_library(library)
    
    # Prepare response
    message = f"Successfully processed {processed_files}/{len(files)} files"
    if errors:
        message += f". Errors: {'; '.join(errors)}"
    
    return MultiSpecUploadResponse(
        message=message,
        files_processed=processed_files,
        total_chunks=len(library['chunks']),
        new_chunks_added=new_chunks_added,
        library_status=SpecLibrary(
            total_files=len(library['metadata']['files']),
            total_chunks=len(library['chunks']),
            files=library['metadata']['files'],
            last_updated=library['metadata'].get('last_updated'),
            storage_path=DATA_PATH
        )
    )

@app.post("/manage-specs")
async def manage_spec_library(request: SpecManagementRequest):
    """
    Manage spec library
    
    Operations:
    - clear: Clear entire library
    - remove: Remove specific file by hash
    - list: List all files (same as GET /spec-library)
    """
    library = load_spec_library()
    
    if request.operation == 'clear':
        # Clear everything
        library = {
            'chunks': [],
            'embeddings': [],
            'metadata': {'files': [], 'total_chunks': 0}
        }
        save_spec_library(library)
        return {"message": "Spec library cleared", "status": "success"}
    
    elif request.operation == 'remove':
        if not request.file_hash:
            raise HTTPException(status_code=400, detail="File hash required for remove operation")
        
        # Find file to remove
        file_to_remove = None
        for f in library['metadata'].get('files', []):
            if f['file_hash'] == request.file_hash:
                file_to_remove = f
                break
        
        if not file_to_remove:
            raise HTTPException(status_code=404, detail="File not found in library")
        
        # This is complex - would need to track which chunks belong to which file
        # For now, just remove from metadata
        library['metadata']['files'] = [
            f for f in library['metadata']['files'] 
            if f['file_hash'] != request.file_hash
        ]
        
        save_spec_library(library)
        return {
            "message": f"Removed {file_to_remove['filename']} from metadata",
            "note": "Chunks remain in library (full rebuild required for complete removal)"
        }
    
    elif request.operation == 'list':
        return SpecLibrary(
            total_files=len(library['metadata'].get('files', [])),
            total_chunks=len(library['chunks']),
            files=library['metadata'].get('files', []),
            last_updated=library['metadata'].get('last_updated'),
            storage_path=DATA_PATH
        )

@app.post("/analyze-audit")
async def analyze_audit(
    file: UploadFile = File(..., description="Audit PDF to analyze")
):
    """Analyze audit against spec library"""
    # Check spec library
    library = load_spec_library()
    if len(library['chunks']) == 0:
        raise HTTPException(
            status_code=400,
            detail="No spec files in library. Please upload spec files first."
        )
    
    # Process audit file
    content = await file.read()
    if len(content) > 100 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="File too large (max 100MB)")
    
    # Extract text
    logger.info(f"Analyzing audit: {file.filename}")
    audit_text = extract_text_from_pdf(content, use_ocr=True)
    
    # Debug: Log sample of extracted text
    logger.info(f"📄 Extracted text sample (first 500 chars): {audit_text[:500]}")
    logger.info(f"📄 Text length: {len(audit_text)} characters")
    
    # Extract infractions using multiple detection methods
    infractions = []
    
    # Method 1: Look for structured INFRACTION patterns (e.g., "INFRACTION #1:", "INFRACTION #2:")
    logger.info("🔍 Method 1: Looking for structured INFRACTION patterns...")
    infraction_pattern = r'INFRACTION\s*#?\d+[:\.]?\s*(.*?)(?=INFRACTION\s*#?\d+|SUMMARY|$)'
    matches = re.finditer(infraction_pattern, audit_text, re.IGNORECASE | re.DOTALL)
    
    method1_count = 0
    for match in matches:
        infraction_text = match.group(0).strip()
        if len(infraction_text) > 20:  # Filter out very short matches
            infractions.append(infraction_text)
            method1_count += 1
    
    logger.info(f"✓ Method 1 found {method1_count} structured infractions")
    
    # Method 1.5: Look for QC Audit format with "Non-Conforming Items"
    if not infractions:
        logger.info("🔍 Method 1.5: Looking for QC Audit non-conforming items pattern...")
        # Look for "Total Number of Non-Conforming Items X"
        nc_pattern = r'Total\s+Number\s+of\s+Non[-\s]?Conforming\s+Items\s+(\d+)'
        nc_match = re.search(nc_pattern, audit_text, re.IGNORECASE)
        
        if nc_match:
            nc_count = int(nc_match.group(1))
            logger.info(f"✓ Found QC Audit with {nc_count} non-conforming items reported")
            
            # Look for checklist items marked "No" or with issues
            lines = audit_text.split('\n')
            for i, line in enumerate(lines):
                line_lower = line.lower()
                # Look for questions/items with "No" answers or issues
                if any(indicator in line_lower for indicator in ['check "no"', 'check no', 'list the items', 'list the issues', 'missing']):
                    # Capture the context around this item
                    start = max(0, i-3)
                    end = min(len(lines), i+7)
                    block = '\n'.join(lines[start:end]).strip()
                    if block and len(block) > 30 and block not in infractions:
                        infractions.append(block)
            
            logger.info(f"✓ Method 1.5 found {len(infractions)} non-conforming items from checklist")
    
    # Method 2: If no structured infractions found, look for keywords
    if not infractions:
        logger.info("🔍 Method 2: Looking for keyword-based infractions...")
        keywords = [
            "go-back", "go back", "goback", 
            "infraction", "violation", "deficiency",
            "non-compliant", "non compliant", "noncompliant",
            "non-conforming", "non conforming", "nonconforming",
            "correction required", "correction needed",
            "does not meet", "fails to meet",
            "not in compliance", "out of compliance",
            "check no", "check \"no\"", "marked no",
            "incomplete", "failed", "missing"
        ]
        
        lines = audit_text.split('\n')
        current_block = []
        
        keyword_matches = []
        for i, line in enumerate(lines):
            line_lower = line.lower()
            matched_keywords = [kw for kw in keywords if kw in line_lower]
            if matched_keywords:
                keyword_matches.append((i, matched_keywords, line[:100]))
                # Capture context (previous and next lines)
                start = max(0, i-2)
                end = min(len(lines), i+5)
                block = '\n'.join(lines[start:end]).strip()
                if block and block not in infractions:
                    infractions.append(block)
        
        logger.info(f"✓ Method 2 found {len(infractions)} keyword-based infractions from {len(keyword_matches)} keyword matches")
        if keyword_matches and len(keyword_matches) <= 5:
            for line_num, kws, line_text in keyword_matches:
                logger.info(f"  Line {line_num}: keywords={kws}, text='{line_text}...'")
    
    if not infractions:
        logger.warning(f"❌ No infractions detected in {file.filename}")
        logger.warning(f"📄 Check if the PDF contains keywords like: go-back, infraction, violation, deficiency, non-compliant")
        return {
            "message": "No infractions found in this audit",
            "infractions": [],
            "audit_file": file.filename,
            "text_length": len(audit_text),
            "text_sample": audit_text[:500] + "..." if len(audit_text) > 500 else audit_text,
            "note": "The analyzer looked for keywords like 'go-back', 'infraction', 'violation', 'deficiency', etc. but found none. Please verify the PDF contains these terms or check the text_sample to see what was extracted."
        }
    
    # Analyze infractions against spec library
    logger.info(f"Found {len(infractions)} infractions, analyzing against {len(library['chunks'])} spec chunks")
    
    results = []
    for i, infraction in enumerate(infractions[:50], 1):  # Limit to 50
        logger.info(f"Analyzing infraction {i}/{min(len(infractions), 50)}")
        
        # Get embedding
        inf_embedding = model.encode([infraction], normalize_embeddings=True)
        
        # Calculate similarities
        cos_scores = util.cos_sim(inf_embedding, library['embeddings'])[0]
        
        # Get top matches
        top_k = 5  # Increased from 3 to 5 for better coverage
        top_indices = cos_scores.argsort(descending=True)[:top_k]
        
        matches = []
        for idx in top_indices:
            score = cos_scores[idx].item()
            if score > 0.4:  # Lowered threshold from 0.5 to 0.4
                chunk = library['chunks'][idx]
                # Extract source file from chunk
                source_match = re.search(r'\[Source: (.*?)\]', chunk)
                source = source_match.group(1) if source_match else "Unknown"
                
                # Clean the chunk text (remove source tag)
                clean_chunk = re.sub(r'\[Source:.*?\]\s*', '', chunk).strip()
                
                matches.append({
                    "source_spec": source,
                    "relevance_score": round(score * 100, 1),
                    "spec_text": clean_chunk[:300] + "..." if len(clean_chunk) > 300 else clean_chunk
                })
        
        # Determine status based on match quality
        if not matches:
            status = "VALID"
            confidence = "LOW"
        elif matches[0]['relevance_score'] > 70:
            status = "POTENTIALLY REPEALABLE"
            confidence = "HIGH"
        elif matches[0]['relevance_score'] > 55:
            status = "POTENTIALLY REPEALABLE"
            confidence = "MEDIUM"
        else:
            status = "VALID"
            confidence = "MEDIUM"
        
        results.append({
            "infraction_id": i,
            "infraction_text": infraction[:500] + "..." if len(infraction) > 500 else infraction,
            "spec_matches": matches,
            "status": status,
            "confidence": confidence,
            "match_count": len(matches)
        })
    
    logger.info(f"Analysis complete: {len(results)} infractions analyzed")
    
    # Enhance with pricing if available
    if PRICING_ENABLED and pricing_analyzer:
        for result in results:
            if result['status'] == 'POTENTIALLY REPEALABLE':
                try:
                    result = enhance_infraction_with_pricing(result, pricing_analyzer)
                except Exception as e:
                    logger.warning(f"Failed to add pricing for infraction {result['infraction_id']}: {e}")
        logger.info("💰 Pricing enhancement complete")
    
    # Transform to frontend-compatible format (for backwards compatibility)
    infractions_frontend = []
    for r in results:
        # Map to old frontend format
        is_repealable = "REPEALABLE" in r['status']
        confidence_value = 0.8 if r['confidence'] == "HIGH" else (0.6 if r['confidence'] == "MEDIUM" else 0.4)
        
        spec_refs = [m['source_spec'] for m in r['spec_matches'][:3]]
        reason = r['spec_matches'][0]['spec_text'][:150] + "..." if r['spec_matches'] else "No matching specifications found"
        
        infractions_frontend.append({
            "code": f"Item {r['infraction_id']}",
            "description": r['infraction_text'][:200] + "..." if len(r['infraction_text']) > 200 else r['infraction_text'],
            "is_repealable": is_repealable,
            "confidence": confidence_value,
            "reason": reason,
            "spec_references": spec_refs,
            "match_count": r['match_count'],
            "status": r['status']
        })
    
    return {
        "audit_file": file.filename,
        "total_spec_files": len(library['metadata'].get('files', [])),
        "total_spec_chunks": len(library['chunks']),
        "infractions_found": len(infractions),
        "infractions_analyzed": len(results),
        "infractions": infractions_frontend,  # Frontend-compatible format
        "analysis_results": results,  # Keep new format too
        "summary": {
            "potentially_repealable": sum(1 for r in results if "REPEALABLE" in r['status']),
            "valid": sum(1 for r in results if r['status'] == "VALID"),
            "high_confidence": sum(1 for r in results if r['confidence'] == "HIGH")
        }
    }

# ============================================
# WEEK 2 ASYNC ENDPOINTS - Celery Integration
# ============================================

try:
    from celery.result import AsyncResult
    from celery_worker import app as celery_app, analyze_audit_async as celery_analyze
    import uuid
    CELERY_AVAILABLE = True
except ImportError:
    CELERY_AVAILABLE = False
    logger.warning("Celery not available - async endpoints disabled")

@app.post("/analyze-audit-async")
async def analyze_audit_async_endpoint(
    file: UploadFile = File(..., description="QA audit PDF to analyze")
):
    """
    Queue audit for async analysis with full infraction detection and repeal recommendations
    Returns job_id immediately for polling
    """
    if not CELERY_AVAILABLE:
        raise HTTPException(503, "Async processing not available")
    
    try:
        # Validate file
        if not file.filename.lower().endswith('.pdf'):
            raise HTTPException(400, "Only PDF files are allowed")
        
        # Read content
        content = await file.read()
        
        if len(content) > 100 * 1024 * 1024:  # 100MB limit
            raise HTTPException(413, "File too large (max 100MB)")
        
        # Queue async task
        task = celery_analyze.delay(content, file.filename)
        
        logger.info(f"Queued async audit analysis: {task.id}")
        
        return {
            "job_id": task.id,
            "status": "queued",
            "message": f"Analysis queued for {file.filename}",
            "poll_url": f"/job-result/{task.id}"
        }
        
    except Exception as e:
        logger.error(f"Failed to queue audit: {e}")
        raise HTTPException(500, f"Failed to start analysis: {str(e)}")

@app.get("/job-result/{job_id}")
async def get_job_result(job_id: str):
    """
    Get async job results with infraction analysis and repeal recommendations
    """
    if not CELERY_AVAILABLE:
        raise HTTPException(503, "Async processing not available")
    
    try:
        result = AsyncResult(job_id, app=celery_app)
        
        if result.state == 'PENDING':
            return {
                "job_id": job_id,
                "status": "pending",
                "message": "Job is queued, waiting for worker..."
            }
        
        elif result.state == 'FAILURE':
            return {
                "job_id": job_id,
                "status": "failed",
                "error": str(result.info) if result.info else "Unknown error"
            }
        
        elif result.state in ['EXTRACTING', 'LOADING', 'ANALYZING', 'FINALIZING']:
            # Progress updates from worker
            meta = result.info or {}
            return {
                "job_id": job_id,
                "status": "processing",
                "state": result.state.lower(),
                "progress": meta.get('progress', 0),
                "message": meta.get('status', 'Processing...')
            }
        
        elif result.state == 'SUCCESS':
            # Complete with results
            analysis = result.result
            
            # Format for easy consumption
            if analysis.get('status') == 'success':
                infractions = analysis.get('infractions', [])
                
                # Separate by confidence
                high_confidence = [i for i in infractions if i.get('confidence', 0) > 80]
                needs_review = [i for i in infractions if i.get('confidence', 0) <= 80]
                
                return {
                    "job_id": job_id,
                    "status": "complete",
                    "summary": {
                        "total_infractions": len(infractions),
                        "auto_repealable": len(high_confidence),
                        "needs_review": len(needs_review),
                        "avg_confidence": sum(i.get('confidence', 0) for i in infractions) / max(1, len(infractions))
                    },
                    "repeals": [
                        {
                            "infraction_id": i['item'],
                            "confidence": i['confidence'],
                            "reasons": [i['reason']],
                            "spec_reference": i.get('source', 'Unknown'),
                            "recommendation": "AUTO_REPEAL" if i['confidence'] > 90 else "REVIEW_RECOMMENDED"
                        }
                        for i in high_confidence
                    ],
                    "review_items": needs_review,
                    "raw_result": analysis
                }
            else:
                return {
                    "job_id": job_id,
                    "status": "failed",
                    "error": analysis.get('error', 'Analysis failed')
                }
        
        else:
            return {
                "job_id": job_id,
                "status": "unknown",
                "state": result.state
            }
            
    except Exception as e:
        logger.error(f"Error checking job {job_id}: {e}")
        return {
            "job_id": job_id,
            "status": "error",
            "error": str(e)
        }

@app.get("/queue-status")
async def get_queue_status():
    """
    Check Celery worker status and queue health
    """
    if not CELERY_AVAILABLE:
        return {
            "workers": {"available": False, "error": "Celery not configured"},
            "status": "disabled"
        }
    
    try:
        inspect = celery_app.control.inspect()
        
        # Ping workers
        active_workers = inspect.ping()
        
        # Get active tasks
        active_tasks = inspect.active()
        active_count = sum(len(tasks) for tasks in active_tasks.values()) if active_tasks else 0
        
        # Get queue stats
        stats = inspect.stats()
        
        return {
            "workers": {
                "available": bool(active_workers),
                "count": len(active_workers) if active_workers else 0,
                "ping": active_workers
            },
            "queue": {
                "active_tasks": active_count
            },
            "stats": stats if stats else {},
            "status": "healthy" if active_workers else "no_workers"
        }
        
    except Exception as e:
        logger.error(f"Queue status error: {e}")
        return {
            "workers": {"available": False, "error": str(e)},
            "status": "error"
        }

@app.post("/batch-analyze")
async def batch_analyze_audits(
    files: List[UploadFile] = File(..., description="Multiple audit PDFs")
):
    """
    Queue multiple audits for parallel processing
    """
    if not CELERY_AVAILABLE:
        raise HTTPException(503, "Async processing not available")
    
    if len(files) > 20:
        raise HTTPException(400, "Maximum 20 files per batch")
    
    jobs = []
    
    for file in files:
        if not file.filename.lower().endswith('.pdf'):
            jobs.append({
                "filename": file.filename,
                "status": "skipped",
                "error": "Not a PDF"
            })
            continue
        
        try:
            content = await file.read()
            
            # Queue task
            task = celery_analyze.delay(content, file.filename)
            
            jobs.append({
                "filename": file.filename,
                "job_id": task.id,
                "status": "queued",
                "poll_url": f"/job-result/{task.id}"
            })
            
        except Exception as e:
            jobs.append({
                "filename": file.filename,
                "status": "failed",
                "error": str(e)
            })
    
    return {
        "batch_id": str(uuid.uuid4())[:8],
        "total": len(files),
        "queued": sum(1 for j in jobs if j['status'] == 'queued'),
        "jobs": jobs
    }

@app.get("/cache-stats")
async def get_cache_stats():
    """
    Get Redis cache statistics and performance metrics
    """
    try:
        # Check if Redis is available
        import redis
        import os
        
        redis_url = os.getenv('REDIS_URL')
        if not redis_url:
            return {
                "status": "disabled",
                "message": "Redis not configured"
            }
        
        # Connect to Redis
        r = redis.from_url(redis_url)
        
        # Get info
        info = r.info()
        
        # Get cache keys
        cache_keys = r.keys('cache:*')
        spec_keys = r.keys('spec:*')
        job_keys = r.keys('celery-task-meta-*')
        
        return {
            "status": "active",
            "memory": {
                "used_memory": info.get('used_memory_human', 'N/A'),
                "used_memory_peak": info.get('used_memory_peak_human', 'N/A'),
                "memory_usage": f"{info.get('used_memory_rss', 0) / (1024*1024):.2f} MB"
            },
            "keys": {
                "total": info.get('db0', {}).get('keys', 0) if 'db0' in info else len(cache_keys + spec_keys + job_keys),
                "cache_entries": len(cache_keys),
                "spec_entries": len(spec_keys),
                "job_results": len(job_keys)
            },
            "performance": {
                "hits": info.get('keyspace_hits', 0),
                "misses": info.get('keyspace_misses', 0),
                "hit_rate": f"{(info.get('keyspace_hits', 0) / max(1, info.get('keyspace_hits', 0) + info.get('keyspace_misses', 0))) * 100:.2f}%",
                "evicted_keys": info.get('evicted_keys', 0)
            },
            "uptime": info.get('uptime_in_seconds', 0)
        }
        
    except ImportError:
        return {
            "status": "disabled",
            "message": "Redis client not installed"
        }
    except Exception as e:
        logger.error(f"Cache stats error: {e}")
        return {
            "status": "error",
            "error": str(e)
        }

# Startup event has been moved to the lifespan handler above

if __name__ == "__main__":
    import uvicorn
    import os
    port = int(os.environ.get("PORT", 8001))
    uvicorn.run(app, host="0.0.0.0", port=port)
    logger.info(f"Server running on port {port}")
