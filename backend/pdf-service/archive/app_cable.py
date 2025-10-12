"""
NEXA AI Document Analyzer - Cable & Ampacity Enhanced Edition
October 06, 2025 - Support for cable replacement, ampacity tables, and underground distribution
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
    title="NEXA AI Document Analyzer - Cable & Ampacity Edition",
    description="Enterprise-grade analysis for cable specs, ampacity tables, and underground distribution",
    version="1.0.0 (October 06, 2025)",
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

# Persistence
EMBEDDINGS_PATH = '/data/spec_embeddings.pkl' if os.path.exists('/data') else 'spec_embeddings.pkl'
logger.info(f"Embeddings will be stored at: {EMBEDDINGS_PATH}")

# Enhanced PG&E patterns for cable and ampacity documents
PGE_PATTERNS = {
    'document_number': r'(?:Document\s*)?(\d{5,6})',
    'revision': r'Rev\.\s*#?\s*(\d+)',
    'effective_date': r'Effective\s+Date:\s*([\d/]+)',
    'purpose': r'Purpose\s+and\s+Scope',
    'references': r'References?:',
    'table': r'Table\s+\d+',
    'figure': r'Figure\s+\d+',
    'notes': r'General\s+Notes?|Notes?:',
    # Cable and ampacity specific patterns
    'ampacity': r'[Aa]mpacity|[Cc]urrent\s+[Cc]apacity|[Cc]onductor\s+[Tt]emp',
    'cable_type': r'XLPE|EPR|PILC|CIC|[Aa]luminum|[Cc]opper',
    'voltage': r'\d+\s*kV|\d+\s*[Vv]olts',
    'temperature': r'\d+\s*°[CF]|\d+\s*degrees',
    'fault': r'[Ff]ault\s+[Ii]ndicator|[Ff]ault\s+[Ll]ocation',
    'replacement': r'[Rr]eplacement|[Rr]epair|[Rr]etirement',
    'underground': r'UG-\d+|[Uu]nderground|[Dd]istribution',
    'greenbook': r'[Gg]reenbook|[Ee]lectric\s+[Pp]lanning\s+[Mm]anual',
    'sealing': r'[Ss]ealing|[Ee]nd\s+[Cc]ap|[Tt]ermination',
    'support': r'[Cc]able\s+[Ss]upport|[Cc]lamp|[Bb]racket'
}

class InfractionAnalysis(BaseModel):
    infraction: str
    status: str
    confidence: float  # 0-100%
    match_count: int
    reasons: List[str]
    matched_documents: List[str]
    severity: str  # HIGH, MEDIUM, LOW
    cable_specific: bool  # Flag for cable/ampacity related infractions

class SpecUploadResponse(BaseModel):
    message: str
    chunks_learned: int
    storage_path: str
    documents_processed: int
    cable_docs_found: int
    ampacity_tables_detected: int
    processing_time: float

def extract_text_from_pdf(file_content: bytes, use_ocr: bool = True) -> tuple:
    """
    Extract text from PDF with OCR support, optimized for ampacity tables
    Returns: (text, ocr_pages, table_count)
    """
    try:
        reader = PdfReader(io.BytesIO(file_content))
        text_parts = []
        ocr_pages = 0
        table_count = 0
        
        for page_num, page in enumerate(reader.pages, 1):
            page_text = page.extract_text()
            
            # Check for tables (ampacity tables often have specific patterns)
            if page_text and re.search(r'(?i)(ampacity|temperature.*rating|conductor.*size)', page_text):
                table_count += 1
                logger.info(f"Detected potential ampacity table on page {page_num}")
            
            # OCR for pages with minimal text or detected tables
            if (not page_text or len(page_text.strip()) < 100 or 'Table' in page_text) and use_ocr:
                try:
                    for image_file_obj in page.images:
                        img = Image.open(io.BytesIO(image_file_obj.data))
                        # Use specific OCR settings for tables
                        ocr_text = pytesseract.image_to_string(img, config='--psm 6')
                        if ocr_text and len(ocr_text.strip()) > 50:
                            page_text = f"[OCR Page {page_num}]\n{ocr_text}"
                            ocr_pages += 1
                            logger.info(f"OCR extracted {len(ocr_text)} chars from page {page_num}")
                            break
                except Exception as ocr_error:
                    logger.warning(f"OCR failed for page {page_num}: {str(ocr_error)}")
            
            if page_text:
                # Add document markers
                doc_match = re.search(PGE_PATTERNS['document_number'], page_text)
                if doc_match:
                    page_text = f"[Document {doc_match.group(1)}]\n{page_text}"
                
                # Mark cable/ampacity specific content
                if re.search(PGE_PATTERNS['ampacity'], page_text, re.IGNORECASE):
                    page_text = f"[AMPACITY CONTENT]\n{page_text}"
                if re.search(PGE_PATTERNS['cable_type'], page_text):
                    page_text = f"[CABLE SPECIFICATION]\n{page_text}"
                
                text_parts.append(page_text)
        
        full_text = '\n'.join(text_parts)
        logger.info(f"Extracted {len(full_text)} chars, OCR: {ocr_pages} pages, Tables: {table_count}")
        
        return full_text, ocr_pages, table_count
    
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"PDF extraction failed: {str(e)}")

def chunk_text_cable_aware(text: str, chunk_size: int = 700) -> List[Dict[str, Any]]:
    """
    Enhanced chunking for cable and ampacity documents
    Larger chunks for tables, maintains table integrity
    """
    # Split by major sections, including cable-specific markers
    section_patterns = [
        r'(Rev\.\s*#?\s*\d+:)',
        r'(Purpose\s+and\s+Scope)',
        r'(General\s+Notes?)',
        r'(References?:)',
        r'(Table\s+\d+)',
        r'(Figure\s+\d+)',
        r'(Document\s+\d{5,6})',
        r'(Greenbook)',
        r'(Electric\s+Planning\s+Manual)',
        r'(UG-\d+)',
        r'(\[AMPACITY CONTENT\])',
        r'(\[CABLE SPECIFICATION\])',
        r'(Ampacity\s+[Tt]able)',
        r'(Conductor\s+[Tt]emperature)',
        r'(Fault\s+[Ii]ndicators?)',
        r'(Cable\s+[Rr]eplacement)'
    ]
    
    combined_pattern = '|'.join(section_patterns)
    sections = re.split(combined_pattern, text, flags=re.IGNORECASE)
    
    chunks = []
    current_chunk = ""
    current_metadata = {
        'document': None,
        'revision': None,
        'section_type': None,
        'is_cable_content': False,
        'is_ampacity_table': False
    }
    
    for section in sections:
        if not section:
            continue
        
        # Check section type and extract metadata
        if re.match(combined_pattern, section, re.IGNORECASE):
            # Extract document number
            if re.search(PGE_PATTERNS['document_number'], section):
                doc_match = re.search(PGE_PATTERNS['document_number'], section)
                current_metadata['document'] = doc_match.group(1) if doc_match else None
            
            # Check for cable/ampacity content
            if 'AMPACITY' in section.upper() or re.search(PGE_PATTERNS['ampacity'], section, re.IGNORECASE):
                current_metadata['is_ampacity_table'] = True
                current_metadata['section_type'] = 'ampacity'
            elif 'CABLE' in section.upper() or re.search(PGE_PATTERNS['cable_type'], section):
                current_metadata['is_cable_content'] = True
                current_metadata['section_type'] = 'cable_spec'
            elif 'Table' in section:
                current_metadata['section_type'] = 'table'
                # Use larger chunk size for tables
                chunk_size = 1000
            elif 'Greenbook' in section or 'Electric Planning' in section:
                current_metadata['section_type'] = 'greenbook'
            elif 'UG-' in section:
                current_metadata['section_type'] = 'underground'
            
            current_chunk = section + " "
        else:
            # Add content with dynamic chunk size
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
                    # Reset chunk size for non-table content
                    if current_metadata['section_type'] != 'table':
                        chunk_size = 700
    
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
    Process and learn from spec book PDF with enhanced cable/ampacity support
    """
    start_time = datetime.now()
    
    try:
        # Extract text with OCR support
        spec_text, ocr_pages, table_count = extract_text_from_pdf(file_content, use_ocr=use_ocr)
        if not spec_text:
            raise HTTPException(status_code=400, detail="No text extracted from spec PDF")
        
        # Extract document numbers and identify cable docs
        doc_numbers = re.findall(PGE_PATTERNS['document_number'], spec_text)
        unique_docs = list(set(doc_numbers))
        
        # Identify cable-specific documents
        cable_docs = []
        cable_doc_numbers = ['050166', '050167', '061324', '039955']  # Known cable/ampacity docs
        for doc in unique_docs:
            if any(cable_num in doc for cable_num in cable_doc_numbers):
                cable_docs.append(doc)
        
        logger.info(f"Found documents: {unique_docs}, Cable docs: {cable_docs}")
        
        # Use cable-aware chunking
        chunk_objects = chunk_text_cable_aware(spec_text)
        chunks = [c['text'] for c in chunk_objects]
        metadata = [c['metadata'] for c in chunk_objects]
        
        # Count ampacity tables
        ampacity_chunks = sum(1 for m in metadata if m.get('is_ampacity_table'))
        
        if not chunks:
            raise HTTPException(status_code=400, detail="No chunks created from spec text")
        
        # Generate embeddings
        logger.info(f"Generating embeddings for {len(chunks)} chunks...")
        embeddings = model.encode(chunks, convert_to_tensor=False, show_progress_bar=True)
        
        # Store with enhanced metadata
        os.makedirs(os.path.dirname(EMBEDDINGS_PATH) if os.path.dirname(EMBEDDINGS_PATH) else '.', exist_ok=True)
        with open(EMBEDDINGS_PATH, 'wb') as f:
            pickle.dump({
                'chunks': chunks,
                'embeddings': embeddings,
                'metadata': metadata,
                'documents': unique_docs,
                'cable_documents': cable_docs,
                'table_count': table_count
            }, f)
        
        processing_time = (datetime.now() - start_time).total_seconds()
        
        return {
            "message": "Spec book learned successfully",
            "chunks_learned": len(chunks),
            "storage_path": EMBEDDINGS_PATH,
            "documents_processed": len(unique_docs),
            "cable_docs_found": len(cable_docs),
            "ampacity_tables_detected": ampacity_chunks,
            "processing_time": processing_time
        }
    
    except Exception as e:
        logger.error(f"Spec learning failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Spec learning failed: {str(e)}")

def extract_cable_infractions(text: str) -> List[Dict[str, Any]]:
    """
    Extract infractions with enhanced patterns for cable and ampacity issues
    """
    # Comprehensive keywords including cable-specific terms
    keywords = [
        "go-back", "go back", "goback",
        "infraction", "violation", "issue",
        "non-compliance", "non-compliant", "noncompliant",
        "defect", "deficiency", "discrepancy",
        "failed", "incorrect", "improper",
        "missing", "inadequate", "insufficient",
        "not per spec", "deviation", "exception",
        # Cable and ampacity specific
        "ampacity", "exceeded ampacity", "over capacity",
        "cable replacement", "cable fault", "cable damage",
        "CIC", "sealing", "end cap", "termination",
        "fault indicator", "fault location",
        "temperature rating", "conductor temp",
        "XLPE", "EPR", "PILC",
        "aluminum cable", "copper cable",
        "underground", "UG-", "greenbook",
        "cable support", "clamp", "bracket"
    ]
    
    lines = text.split('\n')
    infractions = []
    
    for line in lines:
        if any(kw.lower() in line.lower() for kw in keywords):
            cleaned = re.sub(r'\s+', ' ', line.strip())
            if cleaned and len(cleaned) > 20:
                # Extract document reference
                doc_ref = None
                doc_match = re.search(r'(?:per|according to|ref|document)\s*(\d{5,6})', cleaned, re.IGNORECASE)
                if doc_match:
                    doc_ref = doc_match.group(1)
                
                # Determine if cable-related
                is_cable = any(term in cleaned.lower() for term in 
                             ['cable', 'ampacity', 'conductor', 'xlpe', 'epr', 'cic', 'underground'])
                
                # Determine severity
                severity = "MEDIUM"
                if any(word in cleaned.lower() for word in ["critical", "safety", "immediate", "hazard", "exceeded"]):
                    severity = "HIGH"
                elif any(word in cleaned.lower() for word in ["minor", "cosmetic", "optional"]):
                    severity = "LOW"
                
                infractions.append({
                    'text': cleaned,
                    'document_ref': doc_ref,
                    'severity': severity,
                    'is_cable_related': is_cable
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
    
    spec_info = {}
    if spec_learned:
        try:
            with open(EMBEDDINGS_PATH, 'rb') as f:
                data = pickle.load(f)
                spec_info = {
                    'chunks_loaded': len(data.get('chunks', [])),
                    'documents': data.get('documents', []),
                    'cable_documents': data.get('cable_documents', []),
                    'table_count': data.get('table_count', 0)
                }
        except:
            pass
    
    return {
        "name": "NEXA AI Document Analyzer - Cable & Ampacity Edition",
        "version": "1.0.0 (October 06, 2025)",
        "device": device,
        "ocr_available": True,
        "spec_learned": spec_learned,
        "spec_info": spec_info,
        "max_file_size_mb": 700,
        "endpoints": [
            "/health",
            "/upload-spec-book",
            "/analyze-audit",
            "/docs",
            "/redoc"
        ],
        "supported_patterns": list(PGE_PATTERNS.keys()),
        "cable_features": [
            "Ampacity table extraction",
            "Cable replacement criteria",
            "Fault indicator detection",
            "Temperature rating analysis",
            "Underground distribution specs"
        ]
    }

@app.get("/health", response_model=dict)
def health():
    """Health check endpoint"""
    spec_learned = os.path.exists(EMBEDDINGS_PATH)
    
    ocr_status = "not available"
    try:
        version = pytesseract.get_tesseract_version()
        ocr_status = f"available (v{version})"
    except:
        pass
    
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "device": device,
        "spec_learned": spec_learned,
        "embeddings_path": EMBEDDINGS_PATH,
        "ocr_status": ocr_status,
        "model_status": "loaded" if model else "not loaded"
    }

@app.post("/upload-spec-book", response_model=SpecUploadResponse)
async def upload_spec_book(
    file: UploadFile = File(...),
    use_ocr: bool = True
):
    """
    Upload and learn spec book PDF (max 700MB)
    Optimized for ampacity tables and cable specifications
    """
    content = await file.read()
    file_size_mb = len(content) / (1024 * 1024)
    
    if file_size_mb > 700:
        raise HTTPException(status_code=413, detail=f"File too large ({file_size_mb:.1f}MB, max 700MB)")
    
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")
    
    logger.info(f"Processing spec book: {file.filename} ({file_size_mb:.1f}MB, OCR: {use_ocr})")
    
    # Check for known cable/ampacity documents
    cable_keywords = ['ampacity', 'cable', 'underground', 'cic', '050166', '050167', '061324']
    is_cable_doc = any(kw in file.filename.lower() for kw in cable_keywords)
    if is_cable_doc:
        logger.info(f"Detected cable/ampacity document: {file.filename}")
    
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
    Analyze audit PDF for infractions
    Enhanced for cable and ampacity violations
    """
    if not os.path.exists(EMBEDDINGS_PATH):
        raise HTTPException(
            status_code=400,
            detail="Spec book not learned yet. Please upload spec book first."
        )
    
    content = await file.read()
    file_size_mb = len(content) / (1024 * 1024)
    
    if file_size_mb > 700:
        raise HTTPException(status_code=413, detail=f"File too large ({file_size_mb:.1f}MB, max 700MB)")
    
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")
    
    try:
        # Extract audit text
        logger.info(f"Extracting text from audit: {file.filename}")
        audit_text, ocr_pages, _ = extract_text_from_pdf(content, use_ocr=use_ocr)
        
        if not audit_text:
            raise HTTPException(status_code=400, detail="No text could be extracted from audit PDF")
        
        # Extract infractions with cable awareness
        infractions = extract_cable_infractions(audit_text)
        logger.info(f"Found {len(infractions)} potential infractions")
        
        if not infractions:
            return []
        
        # Load spec embeddings
        with open(EMBEDDINGS_PATH, 'rb') as f:
            data = pickle.load(f)
            chunks = data.get('chunks', [])
            embeddings = data.get('embeddings', [])
            metadata = data.get('metadata', [{}] * len(chunks))
            cable_documents = data.get('cable_documents', [])
        
        # Analyze each infraction
        results = []
        
        for inf_obj in infractions[:max_infractions]:
            inf_text = inf_obj['text']
            doc_ref = inf_obj.get('document_ref')
            severity = inf_obj.get('severity', 'MEDIUM')
            is_cable = inf_obj.get('is_cable_related', False)
            
            # Generate embedding
            inf_emb = model.encode([inf_text], convert_to_tensor=False)
            
            # Calculate cosine similarity
            cos_scores = util.cos_sim(inf_emb, embeddings)[0]
            
            # Get more matches for cable-related infractions
            top_k = 8 if is_cable else 5
            top_idx = cos_scores.argsort(descending=True)[:top_k]
            top_scores = cos_scores[top_idx]
            
            # Filter and collect matches
            relevant = []
            matched_docs = set()
            has_cable_match = False
            
            for idx, score in zip(top_idx, top_scores):
                if score.item() > confidence_threshold:
                    chunk_text = chunks[idx]
                    chunk_meta = metadata[idx] if idx < len(metadata) else {}
                    
                    relevant.append((chunk_text, score.item(), chunk_meta))
                    
                    # Track matched documents
                    if chunk_meta.get('document'):
                        doc_num = chunk_meta['document']
                        matched_docs.add(f"Document {doc_num}")
                        
                        # Check if it's a cable document
                        if doc_num in cable_documents:
                            has_cable_match = True
                    
                    # Check for cable content in chunk
                    if chunk_meta.get('is_cable_content') or chunk_meta.get('is_ampacity_table'):
                        has_cable_match = True
            
            match_count = len(relevant)
            
            # Calculate confidence with cable-specific boosting
            if relevant:
                avg_score = sum(score for _, score, _ in relevant) / len(relevant)
                confidence = avg_score * 100
                
                # Boost confidence for cable-specific matches
                if is_cable and has_cable_match:
                    confidence = min(confidence * 1.15, 100)
                elif doc_ref and doc_ref in str(matched_docs):
                    confidence = min(confidence * 1.1, 100)
            else:
                confidence = 0.0
            
            # Enhanced decision logic
            is_repealable = False
            if match_count >= 3 and confidence > 65:
                is_repealable = True
            elif has_cable_match and confidence > 70:
                is_repealable = True
            elif doc_ref and doc_ref in str(matched_docs) and confidence > 60:
                is_repealable = True
            
            # Generate detailed reasons
            reasons = []
            for chunk, score, meta in relevant[:3]:
                chunk_preview = re.sub(r'\s+', ' ', chunk[:200])
                
                doc_info = ""
                if meta.get('document'):
                    doc_info = f"Document {meta['document']}"
                    if meta.get('is_ampacity_table'):
                        doc_info += " (Ampacity Table)"
                    elif meta.get('is_cable_content'):
                        doc_info += " (Cable Specification)"
                
                reason = f"{doc_info} match ({score:.0%} similarity): {chunk_preview}..."
                reasons.append(reason.strip())
            
            # Add specific guidance based on document type
            if any('050166' in doc or '050167' in doc for doc in matched_docs):
                reasons.append("Note: Check ampacity tables for conductor temperature ratings")
            elif '061324' in str(matched_docs):
                reasons.append("Note: Cable replacement criteria - repeated faults or corrosion")
            elif '039955' in str(matched_docs):
                reasons.append("Note: Underground distribution cable specifications apply")
            
            if not reasons:
                reasons = ["No strong spec matches found - infraction appears valid"]
            
            if doc_ref:
                reasons.append(f"Audit references document: {doc_ref}")
            
            results.append(InfractionAnalysis(
                infraction=inf_text[:300] + "..." if len(inf_text) > 300 else inf_text,
                status="REPEALABLE" if is_repealable else "VALID",
                confidence=round(confidence, 1),
                match_count=match_count,
                reasons=reasons,
                matched_documents=list(matched_docs),
                severity=severity,
                cable_specific=is_cable
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
