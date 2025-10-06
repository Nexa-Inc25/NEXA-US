"""
NEXA AI Document Analyzer - FastAPI Backend Service
Handles spec learning, audit analysis, and PDF generation
Optimized for Render Pro deployment with PostgreSQL
"""

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
import fitz  # PyMuPDF
from sentence_transformers import SentenceTransformer
import faiss
import numpy as np
import psycopg2
from psycopg2.extras import execute_values
import os
import time
import json
from datetime import datetime
import io
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table
from reportlab.lib.styles import getSampleStyleSheet
import re
from typing import List

app = FastAPI(title="NEXA AI Document Analyzer API")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize model
model = SentenceTransformer('all-MiniLM-L6-v2')

# Database connection
DB_URL = os.getenv("DATABASE_URL")
if DB_URL:
    conn = psycopg2.connect(DB_URL)
    cursor = conn.cursor()
    
    # Create tables
    cursor.execute("""
        CREATE EXTENSION IF NOT EXISTS vector;
        CREATE TABLE IF NOT EXISTS audit_log (
            id SERIAL PRIMARY KEY,
            user_id VARCHAR(100),
            action VARCHAR(100),
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            details JSONB
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS spec_chunks (
            id SERIAL PRIMARY KEY,
            text TEXT,
            embedding vector(384),
            section_reference VARCHAR(100),
            source_file VARCHAR(255)
        )
    """)
    conn.commit()
else:
    print("Warning: No DATABASE_URL configured, using in-memory storage")
    conn = None
    cursor = None

# Global in-memory storage as fallback
memory_chunks = []
memory_embeddings = None
memory_index = None

def clean_infraction_text(text):
    """Clean and normalize infraction text"""
    text = re.sub(r'\s+', ' ', text.strip())
    text = re.sub(r'([a-z])([A-Z])', r'\1 \2', text)
    text = re.sub(r'(\w)([.,;])', r'\1 \2', text)
    return text

def extract_text(pdf_path, chunk_size=500, batch_size=50):
    """Extract text from PDF with optimized chunking"""
    doc = fitz.open(pdf_path)
    text_chunks = []
    
    for batch_start in range(0, doc.page_count, batch_size):
        batch_end = min(batch_start + batch_size, doc.page_count)
        
        for page_num in range(batch_start, batch_end):
            page = doc[page_num]
            page_text = page.get_text("text")
            
            # Chunk large pages
            for i in range(0, len(page_text), chunk_size):
                chunk = page_text[i:i+chunk_size]
                if chunk.strip():
                    text_chunks.append({
                        'text': chunk,
                        'page': page_num + 1,
                        'source': os.path.basename(pdf_path)
                    })
    
    doc.close()
    return text_chunks

def create_index(all_chunks, user_id):
    """Create FAISS index from text chunks"""
    global memory_chunks, memory_embeddings, memory_index
    
    # Extract text for encoding
    texts = [chunk['text'] for chunk in all_chunks]
    
    # Create embeddings
    embeddings = model.encode(texts, show_progress_bar=False, batch_size=32)
    
    # Create FAISS index
    dimension = embeddings.shape[1]
    index = faiss.IndexFlatL2(dimension)
    index.add(embeddings.astype(np.float32))
    
    if cursor:
        # Store in PostgreSQL
        cursor.execute("TRUNCATE TABLE spec_chunks")
        data = [
            (
                chunk['text'],
                embedding.tolist(),
                f"Page {chunk['page']}",
                chunk['source']
            )
            for chunk, embedding in zip(all_chunks, embeddings)
        ]
        execute_values(
            cursor,
            "INSERT INTO spec_chunks (text, embedding, section_reference, source_file) VALUES %s",
            data,
            template="(%s, %s::vector, %s, %s)"
        )
        
        # Log action
        cursor.execute(
            "INSERT INTO audit_log (user_id, action, details) VALUES (%s, %s, %s)",
            (user_id, "learn_spec", json.dumps({"chunk_count": len(all_chunks)}))
        )
        conn.commit()
    else:
        # Store in memory
        memory_chunks = all_chunks
        memory_embeddings = embeddings
        memory_index = index
    
    return index, embeddings

def extract_infractions(text):
    """Extract infractions using multiple patterns"""
    patterns = [
        r"(?i)(go-back|non-compliant|violation|infraction|deficiency|issue|problem)[:]\s*([^\n.]{10,500})",
        r"(?i)\b(failed to|missing|incorrect|improper)\b\s*([^.!?\n]{10,200})",
    ]
    
    infractions = []
    for pattern in patterns:
        matches = re.findall(pattern, text, re.MULTILINE)
        for match in matches:
            if isinstance(match, tuple) and len(match) >= 2:
                infraction = clean_infraction_text(f"{match[0]}: {match[1]}")
                if infraction not in infractions:
                    infractions.append(infraction)
    
    # Fallback if no infractions found
    if not infractions and text.strip():
        infractions.append(clean_infraction_text(text[:200]))
    
    return infractions

def analyze_infraction(infraction, index, embeddings, text_chunks, confidence_threshold=0.7):
    """Analyze a single infraction against spec"""
    infraction_embedding = model.encode([infraction])[0].astype(np.float32)
    
    # Search in index
    k = min(5, index.ntotal)
    distances, indices = index.search(np.array([infraction_embedding]), k)
    
    # Calculate confidence
    best_distance = distances[0][0] if distances.shape[1] > 0 else float('inf')
    
    if best_distance < 0.3:
        confidence = 0.95
    elif best_distance < 0.5:
        confidence = 0.85
    elif best_distance < 0.7:
        confidence = 0.70
    elif best_distance < 1.0:
        confidence = 0.55
    else:
        confidence = 0.30
    
    # Determine validity and repealability
    validity = confidence >= confidence_threshold
    repealable = not validity
    
    # Get matching spec sections
    reasons = []
    spec_refs = []
    for idx in indices[0][:3]:
        if idx < len(text_chunks):
            chunk = text_chunks[idx]
            reason_text = chunk['text'][:500] if isinstance(chunk, dict) else chunk[:500]
            source = chunk.get('source', 'Unknown') if isinstance(chunk, dict) else 'Spec'
            page = chunk.get('page', 'N/A') if isinstance(chunk, dict) else 'N/A'
            reasons.append(reason_text)
            spec_refs.append(f"{source} - Page {page}")
    
    return {
        "infraction": infraction,
        "validity": "YES" if validity else "NO",
        "repealable": "YES" if repealable else "NO",
        "confidence": round(float(confidence), 2),
        "reasons": reasons,
        "spec_refs": spec_refs
    }

def generate_closeout_pdf(analysis, user_id, analysis_date=None, analysis_depth="Detailed"):
    """Generate PDF closeout report"""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()
    elements = []
    
    # Title and metadata
    elements.append(Paragraph("NEXA AI QA Audit Closeout Report", styles['Title']))
    elements.append(Paragraph(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", styles['Normal']))
    elements.append(Paragraph(f"User: {user_id}", styles['Normal']))
    if analysis_date:
        elements.append(Paragraph(f"Analysis Date: {analysis_date}", styles['Normal']))
    elements.append(Paragraph(f"Analysis Depth: {analysis_depth}", styles['Normal']))
    elements.append(Spacer(1, 12))
    
    # Summary section
    elements.append(Paragraph("Executive Summary", styles['Heading2']))
    total = len(analysis)
    valid = sum(1 for item in analysis if item["validity"] == "YES")
    repealable = sum(1 for item in analysis if item["repealable"] == "YES")
    avg_confidence = sum(item['confidence'] for item in analysis) / total if total > 0 else 0
    
    summary_data = [
        ["Metric", "Value"],
        ["Total Infractions", str(total)],
        ["Valid Infractions", str(valid)],
        ["Repealable Infractions", str(repealable)],
        ["Average Confidence", f"{avg_confidence*100:.1f}%"]
    ]
    
    summary_table = Table(summary_data)
    summary_table.setStyle([
        ('BACKGROUND', (0, 0), (-1, 0), '#f2f2f2'),
        ('GRID', (0, 0), (-1, -1), 1, '#000000'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
    ])
    elements.append(summary_table)
    elements.append(Spacer(1, 12))
    
    # Detailed infractions
    elements.append(Paragraph("Infraction Analysis Details", styles['Heading2']))
    
    for i, item in enumerate(analysis, 1):
        elements.append(Paragraph(f"Infraction {i}", styles['Heading3']))
        elements.append(Paragraph(f"<b>Description:</b> {item['infraction']}", styles['Normal']))
        elements.append(Paragraph(f"<b>Validity:</b> {item['validity']}", styles['Normal']))
        elements.append(Paragraph(f"<b>Repealable:</b> {item['repealable']}", styles['Normal']))
        elements.append(Paragraph(f"<b>Confidence:</b> {item['confidence']*100:.1f}%", styles['Normal']))
        
        if item['reasons']:
            elements.append(Paragraph("<b>Supporting Evidence:</b>", styles['Normal']))
            for reason in item['reasons'][:2]:  # Show top 2 reasons
                elements.append(Paragraph(f"• {reason[:200]}...", styles['Normal']))
        
        if item['spec_refs']:
            elements.append(Paragraph(f"<b>References:</b> {', '.join(item['spec_refs'])}", styles['Normal']))
        
        elements.append(Spacer(1, 6))
    
    doc.build(elements)
    buffer.seek(0)
    return buffer

@app.post("/learn-spec/")
async def learn_spec(spec_files: List[UploadFile] = File(...), user_id: str = "anonymous"):
    """Process and learn from multiple specification PDFs"""
    try:
        all_chunks = []
        
        for spec_file in spec_files:
            # Validate file size
            if spec_file.size > 50 * 1024 * 1024:
                raise HTTPException(status_code=400, detail=f"File {spec_file.filename} exceeds 50 MB")
            
            # Save and process file
            pdf_path = f"/tmp/{spec_file.filename}"
            with open(pdf_path, "wb") as f:
                content = await spec_file.read()
                f.write(content)
            
            # Extract chunks from this PDF
            chunks = extract_text(pdf_path)
            all_chunks.extend(chunks)
            
            # Clean up
            os.remove(pdf_path)
        
        if not all_chunks:
            raise HTTPException(status_code=400, detail="No text extracted from PDFs")
        
        # Create index from all chunks
        index, embeddings = create_index(all_chunks, user_id)
        
        return {
            "success": True,
            "total_chunks": len(all_chunks),
            "files_processed": len(spec_files),
            "message": f"Learned {len(all_chunks)} chunks from {len(spec_files)} spec files"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/analyze-audit/")
async def analyze_audit(
    audit_file: UploadFile = File(...),
    user_id: str = "anonymous",
    confidence_threshold: float = 0.7
):
    """Analyze an audit document for infractions"""
    try:
        # Validate file size
        if audit_file.size > 50 * 1024 * 1024:
            raise HTTPException(status_code=400, detail="File exceeds 50 MB")
        
        # Save and process file
        pdf_path = f"/tmp/{audit_file.filename}"
        with open(pdf_path, "wb") as f:
            content = await audit_file.read()
            f.write(content)
        
        # Extract text and infractions
        audit_chunks = extract_text(pdf_path)
        audit_text = "\n".join([chunk['text'] for chunk in audit_chunks])
        infractions = extract_infractions(audit_text)
        
        # Load spec index
        if cursor:
            cursor.execute("SELECT text, embedding, section_reference, source_file FROM spec_chunks")
            rows = cursor.fetchall()
            if not rows:
                os.remove(pdf_path)
                raise HTTPException(status_code=400, detail="No spec book loaded")
            
            text_chunks = [{'text': row[0], 'ref': row[2], 'source': row[3]} for row in rows]
            embeddings = np.array([row[1] for row in rows], dtype=np.float32)
            index = faiss.IndexFlatL2(embeddings.shape[1])
            index.add(embeddings)
        else:
            # Use in-memory storage
            if memory_index is None:
                os.remove(pdf_path)
                raise HTTPException(status_code=400, detail="No spec book loaded")
            
            text_chunks = memory_chunks
            embeddings = memory_embeddings
            index = memory_index
        
        # Analyze each infraction
        analysis = []
        for infraction in infractions:
            result = analyze_infraction(infraction, index, embeddings, text_chunks, confidence_threshold)
            analysis.append(result)
        
        # Log action
        if cursor:
            cursor.execute(
                "INSERT INTO audit_log (user_id, action, details) VALUES (%s, %s, %s)",
                (user_id, "analyze_audit", json.dumps({"infraction_count": len(analysis)}))
            )
            conn.commit()
        
        # Clean up
        os.remove(pdf_path)
        
        # Summary statistics
        total = len(analysis)
        valid = sum(1 for a in analysis if a['validity'] == "YES")
        repealable = sum(1 for a in analysis if a['repealable'] == "YES")
        avg_confidence = sum(a['confidence'] for a in analysis) / total if total > 0 else 0
        
        return {
            "success": True,
            "summary": {
                "total_infractions": total,
                "valid_infractions": valid,
                "repealable_infractions": repealable,
                "average_confidence": round(avg_confidence, 2)
            },
            "analysis": analysis
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/closeout/generate")
async def closeout_generate(
    request: dict,
    user_id: str = "anonymous"
):
    """Generate PDF closeout report"""
    try:
        analysis = request.get("analysis", [])
        if not analysis:
            raise HTTPException(status_code=400, detail="No analysis data provided")
        
        # Generate PDF
        pdf_buffer = generate_closeout_pdf(
            analysis,
            user_id,
            request.get("analysis_date"),
            request.get("analysis_depth", "Detailed")
        )
        
        # Return as downloadable file
        filename = f"qa_audit_closeout_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        return FileResponse(
            pdf_buffer,
            media_type="application/pdf",
            filename=filename,
            headers={
                "Content-Disposition": f"attachment; filename={filename}"
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate closeout: {str(e)}")

@app.get("/health")
async def health():
    """Health check endpoint"""
    try:
        if cursor:
            cursor.execute("SELECT COUNT(*) FROM spec_chunks")
            chunk_count = cursor.fetchone()[0]
            index_loaded = chunk_count > 0
        else:
            index_loaded = memory_index is not None
            chunk_count = len(memory_chunks) if memory_chunks else 0
        
        return {
            "status": "healthy",
            "service": "nexa-api",
            "index_loaded": index_loaded,
            "chunks_loaded": chunk_count,
            "database_connected": cursor is not None
        }
    except Exception as e:
        return {
            "status": "degraded",
            "error": str(e)
        }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 8000)))
