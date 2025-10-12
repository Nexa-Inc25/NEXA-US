"""
NEXA AI Document Analyzer - October 06, 2025 Latest Edition
Enhanced for large PG&E documents (up to 500MB)
Optimized chunking and confidence calibration
"""
import os
import io
import pickle
import logging
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from sentence_transformers import SentenceTransformer, util
from pypdf import PdfReader
import nltk
import re
import torch
import pandas as pd
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
import pytesseract
from PIL import Image
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Download NLTK data
nltk.download('punkt', quiet=True)

app = FastAPI(
    title="NEXA AI Document Analyzer",
    description="Enterprise-grade document analysis for spec compliance and audit validation",
    version="1.0.0 (October 06, 2025 - Latest)",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add CORS middleware for broader compatibility
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

# Persistence - use /data for Render disk if available
EMBEDDINGS_PATH = '/data/spec_embeddings.pkl' if os.path.exists('/data') else 'spec_embeddings.pkl'
logger.info(f"Embeddings will be stored at: {EMBEDDINGS_PATH}")

# Enhanced PG&E patterns for better extraction
PGE_PATTERNS = {
    'document_number': r'(?:Document\s*)?(\d{5,6})',
    'revision': r'Rev\.\s*#?\s*(\d+)',
    'effective_date': r'Effective\s+Date:\s*([\d/]+)',
    'purpose': r'Purpose\s+and\s+Scope',
    'references': r'References?:',
    'table': r'Table\s+\d+',
    'figure': r'Figure\s+\d+',
    'notes': r'General\s+Notes?|Notes?:',
    # Specific to new docs
    'anchor': r'[Aa]nchor\s+[Rr]od|[Aa]nchor\s+[Ss]pacing',
    'guy': r'[Gg]uy\s+[Ww]ire|[Gg]uy\s+[Mm]arker|[Gg]uy\s+[Gg]rip',
    'pole': r'[Pp]ole\s+[Rr]einforcement|[Pp]ole\s+[Ll]ine',
    'mud_sill': r'[Mm]ud\s+[Ss]ill|[Bb]earing\s+[Pp]late',
}

class InfractionAnalysis(BaseModel):
    infraction: str
    status: str
    confidence: float  # 0-100%
    match_count: int
    reasons: List[str]
    matched_documents: List[str]
    severity: str  # HIGH, MEDIUM, LOW

class SpecUploadResponse(BaseModel):
    message: str
    chunks_learned: int
    storage_path: str
    documents_processed: int
    ocr_pages: int
    processing_time: float

class AnalysisStats(BaseModel):
    total_infractions: int
    repealable: int
    valid: int
    high_confidence: int
    average_confidence: float

def extract_text_from_pdf(file_content: bytes, use_ocr: bool = True) -> tuple:
    """
    Extract text from PDF with OCR support for scanned pages
    Returns: (text, ocr_page_count)
    """
    try:
        reader = PdfReader(io.BytesIO(file_content))
        text_parts = []
        ocr_pages = 0
        
        for page_num, page in enumerate(reader.pages, 1):
            page_text = page.extract_text()
            
            # If minimal text extracted, try OCR
            if (not page_text or len(page_text.strip()) < 100) and use_ocr:
                try:
                    # Extract images from the page
                    for image_file_obj in page.images:
                        img = Image.open(io.BytesIO(image_file_obj.data))
                        ocr_text = pytesseract.image_to_string(img)
                        if ocr_text and len(ocr_text.strip()) > 50:
                            page_text = f"[OCR Page {page_num}]\n{ocr_text}"
                            ocr_pages += 1
                            logger.info(f"OCR extracted {len(ocr_text)} chars from page {page_num}")
                            break
                except Exception as ocr_error:
                    logger.warning(f"OCR failed for page {page_num}: {str(ocr_error)}")
            
            if page_text:
                # Add document markers if found
                doc_match = re.search(PGE_PATTERNS['document_number'], page_text)
                if doc_match:
                    page_text = f"[Document {doc_match.group(1)}]\n{page_text}"
                
                text_parts.append(page_text)
        
        full_text = '\n'.join(text_parts)
        logger.info(f"Extracted {len(full_text)} chars, OCR used on {ocr_pages} pages")
        
        return full_text, ocr_pages
    
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"PDF extraction failed: {str(e)}")

def enhanced_chunk_text(text: str, chunk_size: int = 500) -> List[Dict[str, Any]]:
    """
    Enhanced chunking for large PG&E documents with metadata preservation
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
        r'(Section\s+\d+)',
    ]
    
    combined_pattern = '|'.join(section_patterns)
    sections = re.split(combined_pattern, text, flags=re.IGNORECASE)
    
    chunks = []
    current_chunk = ""
    current_metadata = {
        'document': None,
        'revision': None,
        'section_type': None
    }
    
    for section in sections:
        if not section:
            continue
        
        # Check if this is a section header and extract metadata
        if re.match(combined_pattern, section, re.IGNORECASE):
            # Extract metadata from header
            if re.search(PGE_PATTERNS['document_number'], section):
                doc_match = re.search(PGE_PATTERNS['document_number'], section)
                current_metadata['document'] = doc_match.group(1) if doc_match else None
            
            if re.search(PGE_PATTERNS['revision'], section):
                rev_match = re.search(PGE_PATTERNS['revision'], section)
                current_metadata['revision'] = rev_match.group(1) if rev_match else None
            
            # Determine section type
            if 'Purpose' in section:
                current_metadata['section_type'] = 'purpose'
            elif 'Notes' in section:
                current_metadata['section_type'] = 'notes'
            elif 'Table' in section:
                current_metadata['section_type'] = 'table'
            elif 'Figure' in section:
                current_metadata['section_type'] = 'figure'
            
            current_chunk = section + " "
        else:
            # Add content, creating new chunks as needed
            words = section.split()
            for word in words:
                if len(current_chunk) + len(word) + 1 <= chunk_size:
                    current_chunk += word + " "
                else:
                    # Save current chunk with metadata
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
    
    logger.info(f"Created {len(chunks)} chunks from {len(text)} chars")
    return chunks

def learn_spec_book(file_content: bytes, use_ocr: bool = True) -> dict:
    """
    Process and learn from spec book PDF with enhanced support for large documents
    """
    start_time = datetime.now()
    
    try:
        # Extract text with OCR support
        spec_text, ocr_pages = extract_text_from_pdf(file_content, use_ocr=use_ocr)
        if not spec_text:
            raise HTTPException(status_code=400, detail="No text extracted from spec PDF")
        
        # Extract all document numbers for tracking
        doc_numbers = re.findall(PGE_PATTERNS['document_number'], spec_text)
        unique_docs = list(set(doc_numbers))
        logger.info(f"Found PG&E documents: {unique_docs}")
        
        # Use enhanced chunking
        chunk_objects = enhanced_chunk_text(spec_text)
        chunks = [c['text'] for c in chunk_objects]
        metadata = [c['metadata'] for c in chunk_objects]
        
        if not chunks:
            raise HTTPException(status_code=400, detail="No chunks created from spec text")
        
        # Generate embeddings with progress tracking
        logger.info(f"Generating embeddings for {len(chunks)} chunks...")
        embeddings = model.encode(chunks, convert_to_tensor=False, show_progress_bar=True)
        
        # Store with metadata
        os.makedirs(os.path.dirname(EMBEDDINGS_PATH) if os.path.dirname(EMBEDDINGS_PATH) else '.', exist_ok=True)
        with open(EMBEDDINGS_PATH, 'wb') as f:
            pickle.dump({
                'chunks': chunks,
                'embeddings': embeddings,
                'metadata': metadata,
                'documents': unique_docs
            }, f)
        
        processing_time = (datetime.now() - start_time).total_seconds()
        
        return {
            "message": "Spec book learned successfully",
            "chunks_learned": len(chunks),
            "storage_path": EMBEDDINGS_PATH,
            "documents_processed": len(unique_docs),
            "ocr_pages": ocr_pages,
            "processing_time": processing_time
        }
    
    except Exception as e:
        logger.error(f"Spec learning failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Spec learning failed: {str(e)}")

def extract_enhanced_infractions(text: str) -> List[Dict[str, Any]]:
    """
    Extract infractions with enhanced PG&E-specific patterns
    """
    # Comprehensive keywords for PG&E documents
    keywords = [
        "go-back", "go back", "goback",
        "infraction", "violation", "issue",
        "non-compliance", "non-compliant", "noncompliant",
        "defect", "deficiency", "discrepancy",
        "failed", "incorrect", "improper",
        "missing", "inadequate", "insufficient",
        "not per spec", "deviation", "exception",
        # PG&E specific terms from new docs
        "anchor spacing", "anchor rod corrosion",
        "guy wire tension", "guy marker missing",
        "mud sill", "bearing plate",
        "pole reinforcement", "soft soil",
        "helix diameter", "foam backfill"
    ]
    
    lines = text.split('\n')
    infractions = []
    
    for line in lines:
        if any(kw.lower() in line.lower() for kw in keywords):
            cleaned = re.sub(r'\s+', ' ', line.strip())
            if cleaned and len(cleaned) > 20:
                # Extract document reference if present
                doc_ref = None
                doc_match = re.search(r'(?:per|according to|ref|document)\s*(\d{5,6})', cleaned, re.IGNORECASE)
                if doc_match:
                    doc_ref = doc_match.group(1)
                
                # Determine severity based on keywords
                severity = "MEDIUM"
                if any(word in cleaned.lower() for word in ["critical", "safety", "immediate", "hazard"]):
                    severity = "HIGH"
                elif any(word in cleaned.lower() for word in ["minor", "cosmetic", "optional"]):
                    severity = "LOW"
                
                infractions.append({
                    'text': cleaned,
                    'document_ref': doc_ref,
                    'severity': severity
                })
    
    # Deduplicate while preserving order
    unique_infractions = []
    seen = set()
    for inf in infractions:
        if inf['text'] not in seen:
            seen.add(inf['text'])
            unique_infractions.append(inf)
    
    return unique_infractions

def calibrate_confidence(raw_score: float, match_count: int, has_doc_ref: bool) -> float:
    """
    Calibrate confidence score based on multiple factors
    """
    base_confidence = raw_score * 100
    
    # Boost for multiple matches
    if match_count >= 3:
        base_confidence = min(base_confidence * 1.2, 100)
    elif match_count >= 2:
        base_confidence = min(base_confidence * 1.1, 100)
    
    # Boost if document reference matches
    if has_doc_ref:
        base_confidence = min(base_confidence * 1.15, 100)
    
    # Apply thresholds
    if base_confidence > 80:
        return min(base_confidence, 95)  # Cap high confidence at 95%
    elif base_confidence > 60:
        return base_confidence
    else:
        return max(base_confidence * 0.9, 0)  # Reduce low confidence scores
    
    return base_confidence

@app.get("/", response_model=dict)
def root():
    """API root endpoint with comprehensive system info"""
    spec_learned = os.path.exists(EMBEDDINGS_PATH)
    
    # Load spec info if available
    spec_info = {}
    if spec_learned:
        try:
            with open(EMBEDDINGS_PATH, 'rb') as f:
                data = pickle.load(f)
                spec_info = {
                    'chunks_loaded': len(data.get('chunks', [])),
                    'documents': data.get('documents', [])
                }
        except:
            pass
    
    return {
        "name": "NEXA AI Document Analyzer",
        "version": "1.0.0 (October 06, 2025 - Latest)",
        "device": device,
        "ocr_available": True,
        "spec_learned": spec_learned,
        "spec_info": spec_info,
        "max_file_size_mb": 500,
        "endpoints": [
            "/health",
            "/upload-spec-book",
            "/analyze-audit",
            "/stats",
            "/docs",
            "/redoc"
        ],
        "supported_patterns": list(PGE_PATTERNS.keys())
    }

@app.get("/health", response_model=dict)
def health():
    """Comprehensive health check endpoint"""
    spec_learned = os.path.exists(EMBEDDINGS_PATH)
    
    # Check OCR availability
    ocr_status = "not available"
    try:
        version = pytesseract.get_tesseract_version()
        ocr_status = f"available (v{version})"
    except:
        pass
    
    # Check model status
    model_status = "loaded" if model else "not loaded"
    
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "device": device,
        "spec_learned": spec_learned,
        "embeddings_path": EMBEDDINGS_PATH,
        "ocr_status": ocr_status,
        "model_status": model_status,
        "memory_available": torch.cuda.is_available() if device == 'cuda' else True
    }

@app.post("/upload-spec-book", response_model=SpecUploadResponse)
async def upload_spec_book(
    file: UploadFile = File(...),
    use_ocr: bool = True,
    chunk_size: int = 500
):
    """
    Upload and learn spec book PDF (max 500MB)
    Supports large documents like 70-page "Guys.pdf"
    """
    # Check file size
    content = await file.read()
    file_size_mb = len(content) / (1024 * 1024)
    
    if file_size_mb > 500:
        raise HTTPException(status_code=413, detail=f"File too large ({file_size_mb:.1f}MB, max 500MB)")
    
    # Check file type
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")
    
    logger.info(f"Processing spec book: {file.filename} ({file_size_mb:.1f}MB, OCR: {use_ocr})")
    
    result = learn_spec_book(content, use_ocr=use_ocr)
    return SpecUploadResponse(**result)

@app.post("/analyze-audit", response_model=List[InfractionAnalysis])
async def analyze_audit(
    file: UploadFile = File(...),
    confidence_threshold: float = 0.5,
    use_ocr: bool = True,
    max_infractions: int = 100
):
    """
    Analyze audit PDF for go-back infractions
    Enhanced with calibrated confidence scoring
    """
    if not os.path.exists(EMBEDDINGS_PATH):
        raise HTTPException(
            status_code=400,
            detail="Spec book not learned yet. Please upload spec book first."
        )
    
    # Check file size
    content = await file.read()
    file_size_mb = len(content) / (1024 * 1024)
    
    if file_size_mb > 500:
        raise HTTPException(status_code=413, detail=f"File too large ({file_size_mb:.1f}MB, max 500MB)")
    
    # Check file type
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")
    
    try:
        # Extract audit text
        logger.info(f"Extracting text from audit: {file.filename} ({file_size_mb:.1f}MB)")
        audit_text, ocr_pages = extract_text_from_pdf(content, use_ocr=use_ocr)
        
        if not audit_text:
            raise HTTPException(status_code=400, detail="No text could be extracted from audit PDF")
        
        # Extract infractions with enhanced patterns
        infractions = extract_enhanced_infractions(audit_text)
        logger.info(f"Found {len(infractions)} potential infractions")
        
        if not infractions:
            return []
        
        # Load spec embeddings with metadata
        with open(EMBEDDINGS_PATH, 'rb') as f:
            data = pickle.load(f)
            chunks = data.get('chunks', [])
            embeddings = data.get('embeddings', [])
            metadata = data.get('metadata', [{}] * len(chunks))
            known_documents = data.get('documents', [])
        
        # Analyze each infraction
        results = []
        
        for inf_obj in infractions[:max_infractions]:
            inf_text = inf_obj['text']
            doc_ref = inf_obj.get('document_ref')
            severity = inf_obj.get('severity', 'MEDIUM')
            
            # Generate embedding for infraction
            inf_emb = model.encode([inf_text], convert_to_tensor=False)
            
            # Calculate cosine similarity
            cos_scores = util.cos_sim(inf_emb, embeddings)[0]
            
            # Get top matches - increased for better coverage
            top_k = 7
            top_idx = cos_scores.argsort(descending=True)[:top_k]
            top_scores = cos_scores[top_idx]
            
            # Filter and collect matches
            relevant = []
            matched_docs = set()
            has_doc_ref_match = False
            
            for idx, score in zip(top_idx, top_scores):
                if score.item() > confidence_threshold:
                    chunk_text = chunks[idx]
                    chunk_meta = metadata[idx] if idx < len(metadata) else {}
                    
                    relevant.append((chunk_text, score.item(), chunk_meta))
                    
                    # Track matched documents
                    if chunk_meta.get('document'):
                        matched_docs.add(f"Document {chunk_meta['document']}")
                        if doc_ref and doc_ref == chunk_meta['document']:
                            has_doc_ref_match = True
                    
                    # Check for document number in chunk text
                    doc_match = re.search(PGE_PATTERNS['document_number'], chunk_text)
                    if doc_match:
                        doc_num = doc_match.group(1)
                        matched_docs.add(f"Document {doc_num}")
                        if doc_ref and doc_ref == doc_num:
                            has_doc_ref_match = True
            
            match_count = len(relevant)
            
            # Calculate calibrated confidence
            if relevant:
                avg_score = sum(score for _, score, _ in relevant) / len(relevant)
                confidence = calibrate_confidence(avg_score, match_count, has_doc_ref_match)
            else:
                confidence = 0.0
            
            # Enhanced decision logic
            is_repealable = False
            if match_count >= 3 and confidence > 70:
                is_repealable = True
            elif match_count >= 2 and confidence > 80:
                is_repealable = True
            elif has_doc_ref_match and confidence > 60:
                is_repealable = True
            
            # Generate detailed reasons with PG&E-specific context
            reasons = []
            for chunk, score, meta in relevant[:3]:
                # Clean and format chunk for display
                chunk_preview = re.sub(r'\s+', ' ', chunk[:200])
                
                # Add document info if available
                doc_info = ""
                if meta.get('document'):
                    doc_info = f"Document {meta['document']}"
                    if meta.get('revision'):
                        doc_info += f" Rev. #{meta['revision']}"
                
                # Format reason with context
                reason = f"{doc_info} match ({score:.0%} similarity): {chunk_preview}..."
                reasons.append(reason.strip())
            
            # Add specific messages based on content
            if "anchor" in inf_text.lower() and "022221" in str(matched_docs):
                reasons.append("Note: Minimum spacing 3 times largest helix diameter per 022221")
            elif "guy" in inf_text.lower() and "025998" in str(matched_docs):
                reasons.append("Note: Guy marker requirements may vary in fire-prone areas per 025998")
            elif "mud sill" in inf_text.lower() and "030109" in str(matched_docs):
                reasons.append("Note: Mud sill required for bearing plates per 030109")
            elif "pole reinforcement" in inf_text.lower() and "023058" in str(matched_docs):
                reasons.append("Note: Foam backfill option available for soft soil per 023058")
            
            if not reasons:
                reasons = ["No strong spec matches found - infraction appears valid"]
            
            # Add document reference if provided
            if doc_ref:
                reasons.append(f"Audit references document: {doc_ref}")
            
            results.append(InfractionAnalysis(
                infraction=inf_text[:300] + "..." if len(inf_text) > 300 else inf_text,
                status="REPEALABLE" if is_repealable else "VALID",
                confidence=round(confidence, 1),
                match_count=match_count,
                reasons=reasons,
                matched_documents=list(matched_docs),
                severity=severity
            ))
        
        logger.info(f"Analysis complete: {len(results)} infractions processed")
        return results
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Analysis failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")

@app.get("/stats", response_model=AnalysisStats)
async def get_stats():
    """Get analysis statistics from the last run"""
    # This would typically be stored in a database
    # For now, return sample stats
    return AnalysisStats(
        total_infractions=0,
        repealable=0,
        valid=0,
        high_confidence=0,
        average_confidence=0.0
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=False)
