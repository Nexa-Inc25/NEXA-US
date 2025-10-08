"""
NEXA AI Document Analyzer - October 2025 Version
Enhanced with OCR support and PG&E-specific optimizations
"""
import os
import io
import pickle
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from sentence_transformers import SentenceTransformer, util
from pypdf import PdfReader
import nltk
import re
import torch
import pandas as pd
from typing import List, Optional
from pydantic import BaseModel
import pytesseract  # For OCR on scanned PDFs
from PIL import Image  # For image processing in OCR
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Download NLTK data
nltk.download('punkt', quiet=True)

app = FastAPI(
    title="NEXA AI Document Analyzer",
    description="Enterprise-grade document analysis for spec compliance and audit validation",
    version="1.0.0 (October 2025 Edition)",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Model setup (GPU if available)
device = 'cuda' if torch.cuda.is_available() else 'cpu'
logger.info(f"Using device: {device}")
model = SentenceTransformer('all-MiniLM-L6-v2', device=device)

# Persistence (use /data for Render disk if available)
EMBEDDINGS_PATH = '/data/spec_embeddings.pkl' if os.path.exists('/data') else 'spec_embeddings.pkl'
logger.info(f"Embeddings will be stored at: {EMBEDDINGS_PATH}")

# PG&E specific patterns for better extraction
PGE_PATTERNS = {
    'document_number': r'Document\s+(\d{5,6})',
    'revision': r'Rev\.\s*#?\s*(\d+)',
    'effective_date': r'Effective\s+Date:\s*([\d/]+)',
    'purpose': r'Purpose\s+and\s+Scope',
    'references': r'References?:',
    'table': r'Table\s+\d+',
    'figure': r'Figure\s+\d+',
    'notes': r'General\s+Notes?|Notes?:',
}

class InfractionAnalysis(BaseModel):
    infraction: str
    status: str
    confidence: float  # 0-100%
    match_count: int
    reasons: List[str]
    matched_documents: List[str]  # Added to show which PG&E docs matched

class SpecUploadResponse(BaseModel):
    message: str
    chunks_learned: int
    storage_path: str
    documents_processed: int
    ocr_used: bool

def extract_text_from_pdf(file_content: bytes, use_ocr: bool = False) -> str:
    """Extract text from PDF, with optional OCR for scanned pages"""
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
                # Add PG&E document markers if found
                doc_match = re.search(PGE_PATTERNS['document_number'], page_text)
                if doc_match:
                    page_text = f"[Document {doc_match.group(1)}]\n{page_text}"
                
                text_parts.append(page_text)
        
        if ocr_pages > 0:
            logger.info(f"OCR was used on {ocr_pages} pages")
        
        return '\n'.join(text_parts)
    
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"PDF extraction failed: {str(e)}")

def chunk_text_pge_aware(text: str, chunk_size: int = 500) -> List[dict]:
    """
    Chunk text with PG&E document structure awareness
    Returns chunks with metadata
    """
    # Split by major PG&E document sections
    section_patterns = [
        r'(Rev\.\s*#?\s*\d+:)',
        r'(Purpose\s+and\s+Scope)',
        r'(General\s+Notes?)',
        r'(References?:)',
        r'(Table\s+\d+)',
        r'(Figure\s+\d+)',
        r'(Document\s+\d{5,6})',
    ]
    
    combined_pattern = '|'.join(section_patterns)
    sections = re.split(combined_pattern, text)
    
    chunks = []
    current_chunk = ""
    current_metadata = {}
    
    for section in sections:
        if not section:
            continue
            
        # Check if this is a section header
        if re.match(combined_pattern, section):
            # Extract metadata
            if re.match(PGE_PATTERNS['document_number'], section):
                current_metadata['document'] = section.strip()
            elif re.match(PGE_PATTERNS['revision'], section):
                current_metadata['revision'] = section.strip()
            
            # Add header to current chunk
            current_chunk = section + " "
        else:
            # Add content, creating new chunks as needed
            words = section.split()
            for word in words:
                if len(current_chunk) + len(word) + 1 <= chunk_size:
                    current_chunk += word + " "
                else:
                    # Save current chunk
                    if current_chunk.strip():
                        chunks.append({
                            'text': current_chunk.strip(),
                            'metadata': current_metadata.copy()
                        })
                    current_chunk = word + " "
    
    # Save any remaining chunk
    if current_chunk.strip():
        chunks.append({
            'text': current_chunk.strip(),
            'metadata': current_metadata.copy()
        })
    
    return chunks

def learn_spec_book(file_content: bytes, use_ocr: bool = True) -> dict:
    """Process and learn from spec book PDF with enhanced PG&E support"""
    try:
        spec_text = extract_text_from_pdf(file_content, use_ocr=use_ocr)
        if not spec_text:
            raise HTTPException(status_code=400, detail="No text extracted from spec PDF")
        
        # Extract document numbers for tracking
        doc_numbers = re.findall(PGE_PATTERNS['document_number'], spec_text)
        unique_docs = list(set(doc_numbers))
        logger.info(f"Found PG&E documents: {unique_docs}")
        
        # Use PG&E-aware chunking
        chunk_objects = chunk_text_pge_aware(spec_text)
        chunks = [c['text'] for c in chunk_objects]
        metadata = [c['metadata'] for c in chunk_objects]
        
        if not chunks:
            raise HTTPException(status_code=400, detail="No chunks created from spec text")
        
        # Generate embeddings
        logger.info(f"Generating embeddings for {len(chunks)} chunks...")
        embeddings = model.encode(chunks, convert_to_tensor=False, show_progress_bar=True)
        
        # Store with metadata
        os.makedirs(os.path.dirname(EMBEDDINGS_PATH) if os.path.dirname(EMBEDDINGS_PATH) else '.', exist_ok=True)
        with open(EMBEDDINGS_PATH, 'wb') as f:
            pickle.dump((chunks, embeddings, metadata), f)
        
        return {
            "message": "Spec book learned successfully",
            "chunks_learned": len(chunks),
            "storage_path": EMBEDDINGS_PATH,
            "documents_processed": len(unique_docs),
            "ocr_used": use_ocr
        }
    
    except Exception as e:
        logger.error(f"Spec learning failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Spec learning failed: {str(e)}")

def extract_pge_infractions(text: str) -> List[dict]:
    """Extract infractions with PG&E-specific patterns"""
    # Enhanced keywords for PG&E documents
    keywords = [
        "go-back", "go back", "goback",
        "infraction", "violation", "issue",
        "non-compliance", "non-compliant", "noncompliant",
        "defect", "deficiency", "discrepancy",
        "failed", "incorrect", "improper",
        "missing", "inadequate", "insufficient",
        "not per spec", "deviation", "exception",
        # PG&E specific
        "guy marker", "guy grip", "anchor", "riser",
        "molding", "cable grip", "pole line",
        "rev.", "document", "standard"
    ]
    
    lines = text.split('\n')
    infractions = []
    
    for line in lines:
        if any(kw.lower() in line.lower() for kw in keywords):
            cleaned = re.sub(r'\s+', ' ', line.strip())
            if cleaned and len(cleaned) > 20:
                # Try to extract document reference
                doc_ref = None
                doc_match = re.search(r'(?:per|according to|ref|document)\s*(\d{5,6})', cleaned, re.IGNORECASE)
                if doc_match:
                    doc_ref = doc_match.group(1)
                
                infractions.append({
                    'text': cleaned,
                    'document_ref': doc_ref
                })
    
    # Deduplicate
    unique_infractions = []
    seen = set()
    for inf in infractions:
        if inf['text'] not in seen:
            seen.add(inf['text'])
            unique_infractions.append(inf)
    
    return unique_infractions

@app.get("/", response_model=dict)
def root():
    """API root endpoint with system info"""
    spec_learned = os.path.exists(EMBEDDINGS_PATH)
    return {
        "name": "NEXA AI Document Analyzer",
        "version": "1.0.0 (October 2025 Edition)",
        "device": device,
        "ocr_available": True,
        "spec_learned": spec_learned,
        "endpoints": [
            "/health",
            "/upload-spec-book",
            "/analyze-audit",
            "/docs",
            "/redoc"
        ],
        "pge_patterns_supported": list(PGE_PATTERNS.keys())
    }

@app.get("/health", response_model=dict)
def health():
    """Health check endpoint"""
    spec_learned = os.path.exists(EMBEDDINGS_PATH)
    
    # Try to check OCR
    ocr_status = "unknown"
    try:
        pytesseract.get_tesseract_version()
        ocr_status = "available"
    except:
        ocr_status = "not available"
    
    return {
        "status": "healthy",
        "device": device,
        "spec_learned": spec_learned,
        "embeddings_path": EMBEDDINGS_PATH,
        "ocr_status": ocr_status
    }

@app.post("/upload-spec-book", response_model=SpecUploadResponse)
async def upload_spec_book(
    file: UploadFile = File(...),
    use_ocr: bool = True
):
    """
    Upload and learn spec book PDF (max 300MB)
    Supports OCR for scanned PG&E documents
    """
    # Check file size
    content = await file.read()
    if len(content) > 300 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="File too large (max 300MB)")
    
    # Check file type
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")
    
    logger.info(f"Processing spec book: {file.filename} (OCR: {use_ocr})")
    result = learn_spec_book(content, use_ocr=use_ocr)
    return SpecUploadResponse(**result)

@app.post("/analyze-audit", response_model=List[InfractionAnalysis])
async def analyze_audit(
    file: UploadFile = File(...),
    confidence_threshold: float = 0.5,
    use_ocr: bool = True
):
    """
    Analyze audit PDF for go-back infractions
    Enhanced with PG&E document cross-referencing
    """
    if not os.path.exists(EMBEDDINGS_PATH):
        raise HTTPException(
            status_code=400, 
            detail="Spec book not learned yet. Please upload spec book first."
        )
    
    # Check file size
    content = await file.read()
    if len(content) > 300 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="File too large (max 300MB)")
    
    # Check file type
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")
    
    try:
        # Extract audit text
        logger.info(f"Extracting text from audit: {file.filename}")
        audit_text = extract_text_from_pdf(content, use_ocr=use_ocr)
        if not audit_text:
            raise HTTPException(status_code=400, detail="No text could be extracted from audit PDF")
        
        # Extract infractions with PG&E awareness
        infractions = extract_pge_infractions(audit_text)
        logger.info(f"Found {len(infractions)} potential infractions")
        
        if not infractions:
            return []
        
        # Load spec embeddings with metadata
        with open(EMBEDDINGS_PATH, 'rb') as f:
            data = pickle.load(f)
            if len(data) == 3:
                chunks, embeddings, metadata = data
            else:
                # Fallback for old format
                chunks, embeddings = data
                metadata = [{}] * len(chunks)
        
        # Analyze each infraction
        results = []
        
        for inf_obj in infractions[:100]:  # Limit to 100 per request
            inf_text = inf_obj['text']
            doc_ref = inf_obj.get('document_ref')
            
            # Generate embedding for infraction
            inf_emb = model.encode([inf_text], convert_to_tensor=False)
            
            # Calculate cosine similarity
            cos_scores = util.cos_sim(inf_emb, embeddings)[0]
            
            # Get top matches
            top_k = 7  # Increased for better PG&E doc coverage
            top_idx = cos_scores.argsort(descending=True)[:top_k]
            top_scores = cos_scores[top_idx]
            
            # Filter by threshold and collect matches
            relevant = []
            matched_docs = set()
            
            for idx, score in zip(top_idx, top_scores):
                if score.item() > confidence_threshold:
                    chunk_text = chunks[idx]
                    chunk_meta = metadata[idx] if idx < len(metadata) else {}
                    
                    relevant.append((chunk_text, score.item(), chunk_meta))
                    
                    # Track matched documents
                    if 'document' in chunk_meta:
                        matched_docs.add(chunk_meta['document'])
                    
                    # Check for document number in chunk text
                    doc_match = re.search(PGE_PATTERNS['document_number'], chunk_text)
                    if doc_match:
                        matched_docs.add(f"Document {doc_match.group(1)}")
            
            match_count = len(relevant)
            confidence = (sum(score for _, score, _ in relevant) / top_k * 100) if relevant else 0.0
            
            # Enhanced decision logic for PG&E specs
            # Higher confidence if specific document reference matches
            if doc_ref and any(doc_ref in doc for doc in matched_docs):
                confidence = min(confidence * 1.2, 100.0)  # Boost confidence
            
            is_repealable = match_count >= 2 and confidence > 60
            
            # Generate detailed reasons
            reasons = []
            for chunk, score, meta in relevant[:3]:
                # Clean chunk for display
                chunk_preview = re.sub(r'\s+', ' ', chunk[:200])
                doc_info = meta.get('document', 'Spec')
                reasons.append(
                    f"{doc_info} match ({score:.0%} similarity): {chunk_preview}..."
                )
            
            if not reasons:
                reasons = ["No strong spec matches found - infraction appears valid"]
            
            # Add specific PG&E document references if found
            if doc_ref:
                reasons.append(f"Referenced document: {doc_ref}")
            
            results.append(InfractionAnalysis(
                infraction=inf_text[:300] + "..." if len(inf_text) > 300 else inf_text,
                status="REPEALABLE" if is_repealable else "VALID",
                confidence=round(confidence, 1),
                match_count=match_count,
                reasons=reasons,
                matched_documents=list(matched_docs)
            ))
        
        logger.info(f"Analysis complete: {len(results)} infractions processed")
        return results
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Analysis failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=False)
