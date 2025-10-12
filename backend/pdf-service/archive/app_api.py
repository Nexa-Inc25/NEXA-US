"""
NEXA AI Document Analyzer - FastAPI Version
Enterprise-grade document analysis for spec compliance and audit validation
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

# Download NLTK data
nltk.download('punkt', quiet=True)

app = FastAPI(
    title="NEXA AI Document Analyzer",
    description="Enterprise-grade document analysis for spec compliance and audit validation",
    version="1.0.0"
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
print(f"Using device: {device}")
model = SentenceTransformer('all-MiniLM-L6-v2', device=device)

# Persistence (use /data for Render disk if available)
EMBEDDINGS_PATH = '/data/spec_embeddings.pkl' if os.path.exists('/data') else 'spec_embeddings.pkl'
print(f"Embeddings will be stored at: {EMBEDDINGS_PATH}")

class InfractionAnalysis(BaseModel):
    infraction: str
    status: str
    confidence: float  # 0-100%
    match_count: int
    reasons: List[str]

class SpecUploadResponse(BaseModel):
    message: str
    chunks_learned: int
    storage_path: str

def extract_text_from_pdf(file_content: bytes) -> str:
    """Extract text from PDF file content"""
    try:
        reader = PdfReader(io.BytesIO(file_content))
        text_parts = []
        for page_num, page in enumerate(reader.pages, 1):
            page_text = page.extract_text()
            if page_text:
                text_parts.append(page_text)
        return '\n'.join(text_parts)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"PDF extraction failed: {str(e)}")

def chunk_text(text: str, chunk_size=400) -> List[str]:
    """Chunk text for efficient embedding"""
    sentences = nltk.sent_tokenize(text)
    chunks, current = [], ''
    for sent in sentences:
        if len(current) + len(sent) > chunk_size:
            if current.strip():
                chunks.append(current.strip())
            current = sent
        else:
            current += ' ' + sent
    if current.strip():
        chunks.append(current.strip())
    return chunks

def learn_spec_book(file_content: bytes) -> dict:
    """Process and learn from spec book PDF"""
    try:
        spec_text = extract_text_from_pdf(file_content)
        if not spec_text:
            raise HTTPException(status_code=400, detail="No text extracted from spec PDF")
        
        chunks = chunk_text(spec_text)
        if not chunks:
            raise HTTPException(status_code=400, detail="No chunks created from spec text")
        
        embeddings = model.encode(chunks, convert_to_tensor=False)
        
        # Create directory if doesn't exist
        os.makedirs(os.path.dirname(EMBEDDINGS_PATH) if os.path.dirname(EMBEDDINGS_PATH) else '.', exist_ok=True)
        
        with open(EMBEDDINGS_PATH, 'wb') as f:
            pickle.dump((chunks, embeddings), f)
        
        return {
            "message": "Spec book learned successfully",
            "chunks_learned": len(chunks),
            "storage_path": EMBEDDINGS_PATH
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Spec learning failed: {str(e)}")

def extract_go_back_infractions(text: str) -> List[str]:
    """Extract potential 'go-back' infractions from audit text"""
    keywords = [
        "go-back", "go back", "goback",
        "infraction", "violation", "issue", 
        "non-compliance", "non-compliant", "noncompliant",
        "defect", "deficiency", "discrepancy",
        "failed", "incorrect", "improper",
        "missing", "inadequate", "insufficient"
    ]
    lines = text.split('\n')
    infractions = []
    for line in lines:
        if any(kw.lower() in line.lower() for kw in keywords):
            cleaned = re.sub(r'\s+', ' ', line.strip())
            if cleaned and len(cleaned) > 20:  # Minimum length to avoid noise
                infractions.append(cleaned)
    return list(set(infractions))  # Deduplicate

@app.get("/", response_model=dict)
def root():
    """API root endpoint"""
    return {
        "name": "NEXA AI Document Analyzer",
        "version": "1.0.0",
        "device": device,
        "endpoints": [
            "/health",
            "/upload-spec-book",
            "/analyze-audit",
            "/docs"  # FastAPI auto-generated docs
        ]
    }

@app.get("/health", response_model=dict)
def health():
    """Health check endpoint"""
    spec_learned = os.path.exists(EMBEDDINGS_PATH)
    return {
        "status": "healthy",
        "device": device,
        "spec_learned": spec_learned,
        "embeddings_path": EMBEDDINGS_PATH
    }

@app.post("/upload-spec-book", response_model=SpecUploadResponse)
async def upload_spec_book(file: UploadFile = File(...)):
    """Upload and learn spec book PDF (max 200MB)"""
    # Check file size
    content = await file.read()
    if len(content) > 200 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="File too large (max 200MB)")
    
    # Check file type
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")
    
    result = learn_spec_book(content)
    return SpecUploadResponse(**result)

@app.post("/analyze-audit", response_model=List[InfractionAnalysis])
async def analyze_audit(file: UploadFile = File(...)):
    """Analyze audit PDF for go-back infractions"""
    if not os.path.exists(EMBEDDINGS_PATH):
        raise HTTPException(status_code=400, detail="Spec book not learned yet. Upload spec book first.")
    
    # Check file size
    content = await file.read()
    if len(content) > 200 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="File too large (max 200MB)")
    
    # Check file type
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")
    
    try:
        audit_text = extract_text_from_pdf(content)
        if not audit_text:
            raise HTTPException(status_code=400, detail="No text could be extracted from audit PDF")
        
        # Extract infractions
        infractions = extract_go_back_infractions(audit_text)
        if not infractions:
            return []
        
        # Load spec embeddings
        with open(EMBEDDINGS_PATH, 'rb') as f:
            chunks, embeddings = pickle.load(f)
        
        # Analyze each infraction
        results = []
        confidence_threshold = 0.5  # Adjustable: similarity >0.5 considered match
        
        for inf in infractions[:100]:  # Limit to 100 per request
            inf_emb = model.encode([inf], convert_to_tensor=False)
            
            # Calculate cosine similarity
            cos_scores = util.cos_sim(inf_emb, embeddings)[0]
            
            # Get top matches
            top_k = 5
            top_idx = cos_scores.argsort(descending=True)[:top_k]
            top_scores = cos_scores[top_idx]
            
            # Filter by threshold
            relevant = [(chunks[idx], score.item()) for idx, score in zip(top_idx, top_scores) 
                       if score.item() > confidence_threshold]
            
            match_count = len(relevant)
            confidence = (sum(score for _, score in relevant) / top_k * 100) if relevant else 0.0
            
            # Decision logic
            is_repealable = match_count >= 2 and confidence > 60  # Example: 2+ matches and >60% conf
            
            # Generate reasons
            reasons = []
            for chunk, score in relevant[:3]:
                reasons.append(f"Spec match (similarity {score:.0%}): {chunk[:150]}...")
            if not reasons:
                reasons = ["No strong spec matches found - infraction appears valid"]
            
            results.append(InfractionAnalysis(
                infraction=inf[:200] + "..." if len(inf) > 200 else inf,
                status="REPEALABLE" if is_repealable else "VALID",
                confidence=round(confidence, 1),
                match_count=match_count,
                reasons=reasons
            ))
        
        return results
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=False)
