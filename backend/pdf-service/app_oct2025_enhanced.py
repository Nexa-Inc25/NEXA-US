"""
NEXA AI Document Analyzer - Multi-Spec Support
Enhanced version with multiple spec file support and persistent storage
"""
import os
import io
import pickle
import json
from datetime import datetime
from fastapi import FastAPI, UploadFile, File, HTTPException, Form
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
import hashlib

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# === CPU PERFORMANCE OPTIMIZATION ===
num_cores = int(os.environ.get('RENDER_CORES', len(os.sched_getaffinity(0)) if hasattr(os, 'sched_getaffinity') else cpu_count()))
optimal_threads = max(1, num_cores // 2)

torch.set_num_threads(optimal_threads)
torch.set_num_interop_threads(1)

os.environ.setdefault('OMP_NUM_THREADS', str(optimal_threads))
os.environ.setdefault('MKL_NUM_THREADS', str(optimal_threads))
os.environ.setdefault('PYTORCH_ENABLE_MPS_FALLBACK', '1')

logger.info(f"⚡ CPU Optimization: {num_cores} cores detected, using {optimal_threads} threads")

# Download NLTK data
nltk.download('punkt', quiet=True)

app = FastAPI(
    title="NEXA AI Document Analyzer - Multi-Spec",
    description="Enterprise-grade document analysis with multi-spec file support",
    version="2.0.0 (Multi-Spec Enhanced)",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(RateLimitMiddleware, calls=100, period=60)
app.add_middleware(ErrorHandlingMiddleware)
app.add_middleware(ValidationMiddleware)

# Model setup
device = 'cpu'
logger.info(f"🔧 Using device: {device}")
model = SentenceTransformer('all-MiniLM-L6-v2', device=device)

# Persistence paths
DATA_PATH = '/data' if os.path.exists('/data') else '.'
EMBEDDINGS_PATH = os.path.join(DATA_PATH, 'spec_embeddings.pkl')
SPEC_METADATA_PATH = os.path.join(DATA_PATH, 'spec_metadata.json')

logger.info(f"💾 Data storage path: {DATA_PATH}")

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
                chunks, embeddings = pickle.load(f)
                library['chunks'] = chunks if isinstance(chunks, list) else []
                library['embeddings'] = embeddings if hasattr(embeddings, '__len__') else []
        except Exception as e:
            logger.warning(f"Could not load embeddings: {e}")
    
    # Load metadata if it exists
    if os.path.exists(SPEC_METADATA_PATH):
        try:
            with open(SPEC_METADATA_PATH, 'r') as f:
                metadata = json.load(f)
                library['metadata'] = metadata
        except Exception as e:
            logger.warning(f"Could not load metadata: {e}")
    
    return library

def save_spec_library(library: Dict[str, Any]):
    """Save spec library with metadata"""
    # Create directory if needed
    os.makedirs(DATA_PATH, exist_ok=True)
    
    # Save embeddings
    with open(EMBEDDINGS_PATH, 'wb') as f:
        pickle.dump((library['chunks'], library['embeddings']), f)
    
    # Update metadata
    library['metadata']['total_chunks'] = len(library['chunks'])
    library['metadata']['last_updated'] = datetime.utcnow().isoformat()
    
    # Save metadata
    with open(SPEC_METADATA_PATH, 'w') as f:
        json.dump(library['metadata'], f, indent=2)

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

@app.get("/spec-library", response_model=SpecLibrary)
async def get_spec_library():
    """Get current spec library status"""
    library = load_spec_library()
    
    return SpecLibrary(
        total_files=len(library['metadata'].get('files', [])),
        total_chunks=len(library['chunks']),
        files=library['metadata'].get('files', []),
        last_updated=library['metadata'].get('last_updated'),
        storage_path=DATA_PATH
    )

@app.post("/learn-spec/")
async def learn_single_spec(file: UploadFile = File(...)):
    """Upload and learn a single spec PDF (convenience endpoint)"""
    # Reuse the multi-spec logic with a single file
    files = [file]
    mode = "append"
    
    if mode not in ['append', 'replace']:
        raise HTTPException(status_code=400, detail="Mode must be 'append' or 'replace'")
    
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
    existing_hashes = {f.get('file_hash') for f in library['metadata'].get('files', [])}
    
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
    
    # Add to library
    library['chunks'].extend(chunks)
    library['embeddings'].extend(new_embeddings.tolist() if hasattr(new_embeddings, 'tolist') else new_embeddings)
    
    # Update metadata
    if 'metadata' not in library:
        library['metadata'] = {'files': [], 'last_updated': None}
    
    library['metadata']['files'].append({
        'filename': file.filename,
        'file_hash': file_hash,
        'chunk_count': len(chunks),
        'file_size': file_size,
        'upload_time': time.time()
    })
    library['metadata']['last_updated'] = time.time()
    
    # Save library
    save_spec_library(library)
    
    processing_time = time.time() - start_time
    
    return {
        "message": "Spec book learned successfully",
        "chunks_learned": len(chunks),
        "storage_path": str(DATA_PATH)
    }

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
    
    # Extract infractions (simplified for this example)
    infractions = []
    keywords = ["go-back", "go back", "goback", "infraction", "violation"]
    
    lines = audit_text.split('\n')
    for line in lines:
        if any(kw in line.lower() for kw in keywords):
            infractions.append(line.strip())
    
    if not infractions:
        return {"message": "No infractions found", "infractions": []}
    
    # Analyze infractions against spec library
    results = []
    for infraction in infractions[:50]:  # Limit to 50
        # Get embedding
        inf_embedding = model.encode([infraction], normalize_embeddings=True)
        
        # Calculate similarities
        cos_scores = util.cos_sim(inf_embedding, library['embeddings'])[0]
        
        # Get top matches
        top_k = 3
        top_indices = cos_scores.argsort(descending=True)[:top_k]
        
        matches = []
        for idx in top_indices:
            score = cos_scores[idx].item()
            if score > 0.5:  # Threshold
                chunk = library['chunks'][idx]
                # Extract source file from chunk
                source_match = re.search(r'\[Source: (.*?)\]', chunk)
                source = source_match.group(1) if source_match else "Unknown"
                
                matches.append({
                    "source": source,
                    "score": round(score * 100, 1),
                    "excerpt": chunk[:200] + "..." if len(chunk) > 200 else chunk
                })
        
        results.append({
            "infraction": infraction[:200] + "..." if len(infraction) > 200 else infraction,
            "matches": matches,
            "status": "REPEALABLE" if len(matches) >= 2 and matches[0]['score'] > 60 else "VALID"
        })
    
    return {
        "audit_file": file.filename,
        "spec_files": len(library['metadata'].get('files', [])),
        "infractions_found": len(infractions),
        "infractions_analyzed": len(results),
        "results": results
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
