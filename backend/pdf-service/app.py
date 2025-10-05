from fastapi import FastAPI, UploadFile, File, HTTPException, Depends, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import fitz  # PyMuPDF for optimized large PDF extraction
import io
import re
import os
import jwt
import numpy as np
import faiss
from sentence_transformers import SentenceTransformer
from typing import List, Dict, Any, Optional
import logging
import pickle

# Configure logging for Render
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="NEXA PDF Processing & Analysis Service")

# CORS for Node.js backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Constants for optimization
CHUNK_SIZE = 5000  # Characters per chunk for embeddings
MAX_PAGES = 1500  # Safety limit for very large PDFs
PAGE_BATCH_SIZE = 50  # Process pages in batches to manage memory

# Optimized regex patterns for robust extraction
# Captures document names up to the dash (description separator)
BULLET_REGEX = r'[·•\-\*]\s*([A-Z][A-Z\s&]+?)(?:\s*[-–—]\s*|\n(?=[·•\-\*])|$)'
# For numbered items with multi-line support
NUMBERED_REGEX = r'(\d+)\.\s*([^\n]+(?:\n\s+[^\n\d]+)*)'
# Enhanced infraction patterns - captures multi-line descriptions
INFRACTION_REGEX = r'(?i)(go-back|infraction|violation|issue|problem|deficiency|non-compliance):\s*([^\n]+(?:\n(?!(?:go-back|infraction|violation|issue|problem|deficiency|non-compliance):)[^\n]+)*)'

# Pattern for extracting section headers and their content
SECTION_REGEX = r'(?:^|\n)([A-Z][A-Z\s]{3,30})(?:\n|:)((?:[^\n]+\n?)*?)(?=\n[A-Z][A-Z\s]{3,30}(?:\n|:)|$)'

# AI Model and Index Configuration
security = HTTPBearer()
model = SentenceTransformer('all-MiniLM-L6-v2')
INDEX_PATH = "/data/spec_index.faiss" if os.path.exists("/data") else "./spec_index.faiss"
CHUNKS_PATH = "/data/spec_chunks.pkl" if os.path.exists("/data") else "./spec_chunks.pkl"
EMBEDDINGS_PATH = "/data/spec_embeddings.npy" if os.path.exists("/data") else "./spec_embeddings.npy"

# Auth0 Configuration (Optional - can be disabled for local testing)
AUTH_ENABLED = os.environ.get("AUTH_ENABLED", "false").lower() == "true"
AUTH0_DOMAIN = os.environ.get("AUTH0_DOMAIN", "dev-kbnx7pja3zpg0lud.us.auth0.com")
AUTH0_AUDIENCE = os.environ.get("AUTH0_AUDIENCE", "https://api.nexa.local")

# Global index storage
spec_index = None
spec_chunks = []

def load_index():
    """Load persisted FAISS index and chunks from disk."""
    global spec_index, spec_chunks
    if os.path.exists(INDEX_PATH) and os.path.exists(CHUNKS_PATH):
        try:
            spec_index = faiss.read_index(INDEX_PATH)
            with open(CHUNKS_PATH, 'rb') as f:
                spec_chunks = pickle.load(f)
            logger.info(f"Loaded index with {spec_index.ntotal} vectors and {len(spec_chunks)} chunks")
            return spec_index, spec_chunks
        except Exception as e:
            logger.error(f"Error loading index: {e}")
    return None, []

async def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Verify JWT token if authentication is enabled."""
    if not AUTH_ENABLED:
        return {"sub": "dev-user"}  # Bypass for local testing
    
    try:
        token = credentials.credentials
        jwks_client = jwt.PyJWKClient(f"https://{AUTH0_DOMAIN}/.well-known/jwks.json")
        signing_key = jwks_client.get_signing_key_from_jwt(token)
        payload = jwt.decode(
            token, 
            signing_key.key, 
            algorithms=["RS256"], 
            audience=AUTH0_AUDIENCE,
            issuer=f"https://{AUTH0_DOMAIN}/"
        )
        return payload
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {str(e)}")

# Conditional dependency for auth
auth_dependency = [Depends(verify_token)] if AUTH_ENABLED else []

@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "service": "pdf-processor",
        "auth_enabled": AUTH_ENABLED,
        "index_loaded": spec_index is not None
    }

@app.post("/parse-job-pdf/")
async def parse_job_pdf(job_file: UploadFile = File(...)):
    """
    Optimized PDF parsing with dynamic document list extraction.
    Uses enhanced regex for bullet lists and multi-line content.
    """
    if not job_file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="File must be a PDF")
    
    content = await job_file.read()
    
    # Response structure
    materials = {"headers": [], "rows": []}
    instructions = []
    gps_links = []
    chunks = []  # For spec learning
    found_docs = []
    missing_docs = []
    permits = []
    required_docs = []  # Dynamically extracted
    
    try:
        # Open PDF from memory stream (efficient for large files)
        doc = fitz.open(stream=content, filetype="pdf")
        total_pages = min(len(doc), MAX_PAGES)
        
        logger.info(f"Processing {job_file.filename}: {total_pages} pages")
        
        # First pass: collect all text for dynamic document extraction
        full_text = ""
        for page in doc:
            full_text += page.get_text("text") + "\n"
        
        # Dynamically extract required documents list
        if "AS-BUILT ORDER" in full_text.upper() or "AS BUILT ORDER" in full_text.upper():
            # Extract the AS-BUILT ORDER section
            order_match = re.search(r'AS[\-\s]?BUILT ORDER[:\s]*(.*?)(?=\n[A-Z]{4,}|\n\n\n|\Z)', full_text, re.IGNORECASE | re.DOTALL)
            if order_match:
                order_section = order_match.group(1)
                # Extract bullet items
                bullet_items = re.findall(BULLET_REGEX, order_section, re.MULTILINE)
                # Also check for numbered items
                numbered_items = re.findall(NUMBERED_REGEX, order_section, re.MULTILINE)
                
                # Combine and clean
                for item in bullet_items:
                    cleaned = item.strip().replace('\n', ' ')
                    if cleaned and len(cleaned) > 3:
                        required_docs.append(cleaned)
                
                for num, item in numbered_items:
                    cleaned = item.strip().replace('\n', ' ')
                    if cleaned and len(cleaned) > 3:
                        required_docs.append(cleaned)
        
        # Fallback to default list if extraction failed
        if not required_docs:
            required_docs = [
                'POLE BILL', 'EC TAG', 'PG&E FACE SHEET',
                'EQUIPMENT & POLE INFORMATION', 'CONSTRUCTION FEEDBACK',
                'CREW INSTRUCTIONS', 'CREW MATERIALS', 'MAP',
                'JP FORMS', 'CCSC'
            ]
        
        # Process pages in batches for detailed extraction
        for batch_start in range(0, total_pages, PAGE_BATCH_SIZE):
            batch_end = min(batch_start + PAGE_BATCH_SIZE, total_pages)
            batch_text = ""
            
            for page_num in range(batch_start, batch_end):
                page = doc[page_num]
                page_text = page.get_text("text")
                batch_text += page_text + "\n"
                
                # Chunk for embeddings/learning
                if len(page_text) > CHUNK_SIZE:
                    for i in range(0, len(page_text), CHUNK_SIZE):
                        chunks.append({
                            "text": page_text[i:i+CHUNK_SIZE],
                            "page": page_num + 1
                        })
                elif page_text.strip():
                    chunks.append({
                        "text": page_text,
                        "page": page_num + 1
                    })
                
                # Extract CREW MATERIALS with enhanced patterns
                if "CREW MATERIALS" in page_text.upper():
                    materials = extract_materials_enhanced(page_text)
                
                # Extract CREW INSTRUCTIONS with multi-line support
                if "CREW INSTRUCTIONS" in page_text.upper():
                    instructions.extend(extract_instructions_enhanced(page_text))
                
                # GPS extraction with context
                gps_coords = extract_gps_coordinates(page_text, page_num + 1)
                gps_links.extend(gps_coords)
            
            # Extract permits and documents from batch
            permits.extend(extract_permits(batch_text))
            found_docs.extend(check_documents(batch_text))
        
        doc.close()
        
        # Check which required documents are present/missing
        # Use dynamically extracted list or fallback
        for doc in required_docs:
            # Check if document is mentioned in the full text
            if re.search(rf'\b{re.escape(doc)}\b', full_text, re.IGNORECASE):
                found_docs.append(doc)
        
        # Determine missing documents
        missing_docs = [doc for doc in required_docs if doc not in found_docs]
        
    except Exception as e:
        logger.error(f"Error processing PDF: {str(e)}")
        raise HTTPException(status_code=500, detail=f"PDF processing failed: {str(e)}")
    
    return {
        "success": True,
        "required_docs": required_docs,  # Dynamically extracted list
        "materials": materials,
        "instructions": instructions[:20],  # Limit to 20 instructions
        "gps_links": gps_links,
        "chunks": chunks[:100],  # Return first 100 chunks for preview
        "total_chunks": len(chunks),
        "found_docs": list(set(found_docs)),
        "missing_docs": missing_docs,
        "permits": list(set(permits)),
        "total_pages": total_pages,
        "file_size": len(content),
        # Legacy fields for compatibility
        "materials_text": '\n'.join([' - '.join(row) for row in materials.get("rows", [])]) if materials.get("rows") else "No materials found",
        "instructions_text": '\n'.join(instructions) if instructions else "No instructions found"
    }

def extract_materials_enhanced(text: str) -> Dict:
    """
    Enhanced materials extraction using optimized regex patterns.
    Handles bullet lists, numbered lists, and table structures.
    """
    materials = {"headers": [], "rows": []}
    
    # Extract CREW MATERIALS section
    section_match = re.search(r'CREW MATERIALS[:\s]*(.*?)(?=\n[A-Z]{4,}[\s:]|\n\n\n|\Z)', text, re.IGNORECASE | re.DOTALL)
    if not section_match:
        return materials
    
    section_text = section_match.group(1)
    
    # Try to detect table structure first
    lines = section_text.strip().split('\n')[:30]  # Limit to first 30 lines
    
    # Check for table with tabs or multiple spaces
    table_lines = []
    for line in lines:
        if '\t' in line or re.search(r'\s{3,}', line):
            table_lines.append(line)
    
    if len(table_lines) >= 2:
        # Process as table
        for i, line in enumerate(table_lines):
            cols = re.split(r'\t|\s{3,}', line)
            cols = [c.strip() for c in cols if c.strip()]
            
            if i == 0 and len(cols) > 1:
                materials["headers"] = cols
            elif len(cols) > 0:
                materials["rows"].append(cols)
    else:
        # Process as bullet/numbered list
        bullets = re.findall(BULLET_REGEX, section_text, re.MULTILINE)
        numbered = re.findall(NUMBERED_REGEX, section_text, re.MULTILINE)
        
        materials["headers"] = ["Item", "Description"]
        
        for bullet in bullets:
            cleaned = bullet.strip().replace('\n', ' ')
            if ':' in cleaned:
                parts = cleaned.split(':', 1)
                materials["rows"].append([parts[0].strip(), parts[1].strip()])
            elif cleaned:
                materials["rows"].append([cleaned.split()[0] if cleaned.split() else cleaned, cleaned])
        
        for num, item in numbered:
            cleaned = item.strip().replace('\n', ' ')
            if ':' in cleaned:
                parts = cleaned.split(':', 1)
                materials["rows"].append([parts[0].strip(), parts[1].strip()])
            elif cleaned:
                materials["rows"].append([f"Item {num}", cleaned])
    
    return materials

def extract_instructions_enhanced(text: str) -> List[str]:
    """
    Enhanced instructions extraction with multi-line support.
    Handles complex formatting and indentation.
    """
    instructions = []
    
    # Extract CREW INSTRUCTIONS section
    section_match = re.search(r'CREW INSTRUCTIONS[:\s]*(.*?)(?=\n[A-Z]{4,}[\s:]|\n\n\n|\Z)', text, re.IGNORECASE | re.DOTALL)
    if not section_match:
        return instructions
    
    section_text = section_match.group(1)
    
    # Extract bullet items (handles multi-line)
    bullets = re.findall(BULLET_REGEX, section_text, re.MULTILINE)
    for bullet in bullets:
        cleaned = bullet.strip().replace('\n', ' ').replace('  ', ' ')
        if cleaned and len(cleaned) > 5:
            instructions.append(cleaned)
    
    # Extract numbered items (handles multi-line)
    numbered = re.findall(NUMBERED_REGEX, section_text, re.MULTILINE)
    for num, item in numbered:
        cleaned = item.strip().replace('\n', ' ').replace('  ', ' ')
        if cleaned and len(cleaned) > 5:
            instructions.append(f"{num} {cleaned}")
    
    # If no bullets or numbers found, try paragraph-based extraction
    if not instructions:
        paragraphs = section_text.split('\n\n')
        for para in paragraphs[:10]:  # Limit to first 10 paragraphs
            cleaned = para.strip().replace('\n', ' ')
            if cleaned and len(cleaned) > 10 and not re.match(r'^[A-Z\s]{10,}:', cleaned):
                instructions.append(cleaned)
    
    return instructions[:20]  # Return max 20 instructions

def extract_gps_coordinates(text: str, page_num: int) -> List[Dict]:
    """Extract GPS coordinates with context."""
    gps_links = []
    patterns = [
        r'(\d{2,3}\.\d{4,6})[,\s]+(-?\d{2,3}\.\d{4,6})',
        r'lat[:\s]*(\d{2,3}\.\d{4,6})[,\s]*lon[g]?[:\s]*(-?\d{2,3}\.\d{4,6})',
        r'GPS[:\s]*(\d{2,3}\.\d{4,6})[,\s]+(-?\d{2,3}\.\d{4,6})',
    ]
    
    for pattern in patterns:
        matches = re.finditer(pattern, text, re.IGNORECASE)
        for match in matches:
            lat, lng = float(match.group(1)), float(match.group(2))
            if -90 <= lat <= 90 and -180 <= lng <= 180:
                # Extract context
                start = max(0, match.start() - 50)
                end = min(len(text), match.end() + 50)
                context = text[start:end].replace('\n', ' ').strip()
                
                gps_links.append({
                    "coordinates": f"{lat},{lng}",
                    "googleMapsUrl": f"https://maps.google.com/?q={lat},{lng}",
                    "label": f"Location Page {page_num}",
                    "page": page_num,
                    "context": context
                })
    
    return gps_links

def extract_permits(text: str) -> List[str]:
    """Extract permit numbers from text."""
    permits = []
    patterns = [
        r'permit[#\s:]*([A-Z0-9\-]+)',
        r'PM[#\s:]*(\d{8})',  # PG&E PM numbers
        r'work\s*order[#\s:]*([A-Z0-9\-]+)',
    ]
    
    for pattern in patterns:
        matches = re.finditer(pattern, text, re.IGNORECASE)
        for match in matches:
            permit = match.group(1)
            if len(permit) >= 5:  # Valid permit length
                permits.append(permit)
    
    return permits

def check_documents(text: str) -> List[str]:
    """Check which required documents are present."""
    found = []
    docs_to_check = [
        'POLE BILL', 'EC TAG', 'PG&E FACE SHEET',
        'EQUIPMENT & POLE INFORMATION', 'CONSTRUCTION FEEDBACK',
        'CREW INSTRUCTIONS', 'CREW MATERIALS', 'MAP',
        'JP FORMS', 'CCSC'
    ]
    
    for doc in docs_to_check:
        if doc.upper() in text.upper():
            found.append(doc)
    
    return found

@app.post("/learn-spec/", dependencies=auth_dependency)
async def learn_spec(spec_file: UploadFile = File(...)):
    """
    Process large spec books for learning/indexing with embeddings.
    Creates FAISS index for similarity search.
    """
    global spec_index, spec_chunks
    
    if not spec_file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="File must be a PDF")
    
    content = await spec_file.read()
    chunks = []
    
    try:
        doc = fitz.open(stream=content, filetype="pdf")
        total_pages = min(len(doc), MAX_PAGES)
        
        logger.info(f"Learning spec {spec_file.filename}: {total_pages} pages")
        
        # Extract text chunks
        for page_num in range(total_pages):
            page = doc[page_num]
            text = page.get_text("text")
            
            if text.strip():
                # Chunk large pages
                for i in range(0, len(text), CHUNK_SIZE):
                    chunk_text = text[i:i+CHUNK_SIZE]
                    chunks.append(chunk_text)
        
        doc.close()
        
        if not chunks:
            raise HTTPException(status_code=400, detail="No text content found in PDF")
        
        # Create embeddings for all chunks
        logger.info(f"Creating embeddings for {len(chunks)} chunks...")
        embeddings = model.encode(chunks, show_progress_bar=True, batch_size=32)
        
        # Create FAISS index
        dimension = embeddings.shape[1]
        spec_index = faiss.IndexFlatL2(dimension)  # L2 distance for similarity
        spec_index.add(np.array(embeddings))
        
        # Save chunks and index
        spec_chunks = chunks
        
        # Persist to disk
        try:
            faiss.write_index(spec_index, INDEX_PATH)
            with open(CHUNKS_PATH, 'wb') as f:
                pickle.dump(spec_chunks, f)
            np.save(EMBEDDINGS_PATH, embeddings)
            logger.info(f"Saved index and chunks to disk")
        except Exception as e:
            logger.warning(f"Could not persist index: {e}")
        
    except Exception as e:
        logger.error(f"Error processing spec: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Spec processing failed: {str(e)}")
    
    return {
        "success": True,
        "total_chunks": len(chunks),
        "total_pages": total_pages,
        "index_size": spec_index.ntotal,
        "embedding_dim": dimension,
        "message": f"Spec book learned: {len(chunks)} chunks indexed from {total_pages} pages"
    }

@app.post("/analyze-audit/", dependencies=auth_dependency)
async def analyze_audit(audit_file: UploadFile = File(...)):
    """
    Analyze audit PDF for infractions and determine if repealable.
    Cross-references against learned spec book for confidence scoring.
    """
    global spec_index, spec_chunks
    
    # Load index if not in memory
    if spec_index is None:
        spec_index, spec_chunks = load_index()
        if spec_index is None:
            raise HTTPException(status_code=400, detail="No spec book learned. Please upload a spec first.")
    
    if not audit_file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="File must be a PDF")
    
    content = await audit_file.read()
    
    try:
        doc = fitz.open(stream=content, filetype="pdf")
        audit_text = ""
        
        # Extract all text from audit
        for page in doc:
            audit_text += page.get_text("text") + "\n"
        
        doc.close()
        
        # Extract infractions using optimized regex for multi-line descriptions
        # Primary pattern: captures multi-line descriptions properly
        primary_matches = re.findall(INFRACTION_REGEX, audit_text, re.MULTILINE | re.DOTALL)
        
        # Secondary patterns for additional formats
        secondary_patterns = [
            r'(?i)\b(failed to|missing|incorrect|improper|insufficient)\b\s*([^.!?\n]{10,200}(?:\n(?![A-Z]{4,})[^.!?\n]{0,100})*)',
            r'(?i)(?:item\s*\d+[:\.]?\s*)(.*?(?:violation|infraction|issue|problem)[^.!?\n]*(?:\n(?![A-Z]{4,})[^.!?\n]{0,100})*)',
        ]
        
        infractions = []
        
        # Process primary matches
        for match in primary_matches:
            if isinstance(match, tuple) and len(match) >= 2:
                # Clean multi-line description
                description = match[1].strip()
                # Replace multiple newlines with single space
                description = re.sub(r'\s*\n\s*', ' ', description)
                # Clean extra whitespace
                description = re.sub(r'\s+', ' ', description)
                
                infraction_text = f"{match[0]}: {description}"
                if len(infraction_text) > 20 and len(infraction_text) < 1000:
                    infractions.append(infraction_text)
        
        # Process secondary patterns
        for pattern in secondary_patterns:
            matches = re.findall(pattern, audit_text, re.MULTILINE | re.DOTALL)
            for match in matches:
                if isinstance(match, tuple):
                    description = match[1].strip() if len(match) > 1 else match[0]
                    description = re.sub(r'\s*\n\s*', ' ', description)
                    description = re.sub(r'\s+', ' ', description)
                    
                    infraction_text = f"{match[0]}: {description}"
                else:
                    infraction_text = match
                
                # Clean up and filter
                infraction_text = infraction_text.strip()
                if len(infraction_text) > 20 and len(infraction_text) < 1000:
                    infractions.append(infraction_text)
        
        # Remove duplicates while preserving order
        seen = set()
        unique_infractions = []
        for inf in infractions:
            if inf.lower() not in seen:
                seen.add(inf.lower())
                unique_infractions.append(inf)
        
        # Analyze each infraction
        results = []
        for infraction in unique_infractions[:20]:  # Limit to 20 infractions
            # Embed the infraction
            inf_embedding = model.encode([infraction])
            
            # Search in spec index
            k = min(5, spec_index.ntotal)  # Top 5 matches or less
            distances, indices = spec_index.search(inf_embedding, k=k)
            
            # Calculate confidence based on distance
            # Lower distance = higher similarity
            best_distance = distances[0][0] if distances.shape[1] > 0 else float('inf')
            
            # Convert L2 distance to confidence percentage
            # Typical L2 distances range from 0 to 2 for normalized embeddings
            if best_distance < 0.3:  # Very similar
                confidence = 95.0
            elif best_distance < 0.5:  # Similar
                confidence = 85.0
            elif best_distance < 0.7:  # Somewhat similar
                confidence = 70.0
            elif best_distance < 1.0:  # Loosely related
                confidence = 55.0
            elif best_distance < 1.5:  # Weakly related
                confidence = 40.0
            else:  # Not related
                confidence = 20.0
            
            # Determine if repealable (>50% confidence)
            repealable = confidence > 50
            
            # Get matching spec sections as reasons
            reasons = []
            if repealable:
                for idx, dist in zip(indices[0], distances[0]):
                    if dist < 1.0 and idx < len(spec_chunks):  # Only include relevant matches
                        chunk = spec_chunks[idx]
                        # Truncate long chunks for readability
                        reason = chunk[:300] + "..." if len(chunk) > 300 else chunk
                        reasons.append({
                            "text": reason,
                            "similarity": float(1.0 - (dist / 2.0)),  # Convert to similarity score
                            "chunk_index": int(idx)
                        })
            
            results.append({
                "infraction": infraction,
                "repealable": repealable,
                "confidence": round(confidence, 2),
                "best_distance": float(best_distance),
                "reasons": reasons[:3]  # Top 3 reasons
            })
        
        # Summary statistics
        total_infractions = len(results)
        repealable_count = sum(1 for r in results if r["repealable"])
        avg_confidence = np.mean([r["confidence"] for r in results]) if results else 0
        
    except Exception as e:
        logger.error(f"Error analyzing audit: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Audit analysis failed: {str(e)}")
    
    return {
        "success": True,
        "summary": {
            "total_infractions": total_infractions,
            "repealable_count": repealable_count,
            "non_repealable_count": total_infractions - repealable_count,
            "average_confidence": round(avg_confidence, 2),
            "spec_chunks_searched": len(spec_chunks)
        },
        "analysis": results,
        "message": f"Found {total_infractions} infractions, {repealable_count} are repealable"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
