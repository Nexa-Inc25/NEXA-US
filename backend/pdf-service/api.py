"""
NEXA AI Document Analyzer - FastAPI Backend Service
Handles spec learning, audit analysis, and PDF generation
Optimized for Render Pro deployment with PostgreSQL
"""

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pypdf import PdfReader  # Using pypdf instead of PyMuPDF for faster builds
from sentence_transformers import SentenceTransformer
import faiss
import numpy as np
import psycopg2
from psycopg2.extras import execute_values
import os
import time
import json
import asyncio
from datetime import datetime
import io
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table
from reportlab.lib.styles import getSampleStyleSheet
import re
from functools import lru_cache
from typing import List, Optional
import math
import logging
from urllib.parse import urlparse, urlunparse

app = FastAPI(title="NEXA AI Document Analyzer API")

# Logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(level=LOG_LEVEL, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("nexa")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Config (override via environment, see .env.example)
CHUNK_SIZE_DEFAULT = int(os.getenv("CHUNK_SIZE", "500"))
PAGE_BATCH_SIZE_DEFAULT = int(os.getenv("PAGE_BATCH_SIZE", "50"))
MAX_PAGES_DEFAULT = int(os.getenv("MAX_PAGES", "1500"))
# HNSW tuning (Option 2 speed-focused defaults)
HNSW_M = int(os.getenv("HNSW_M", "16"))
HNSW_EF_CONSTRUCTION = int(os.getenv("HNSW_EF_CONSTRUCTION", "80"))
HNSW_EF_SEARCH = int(os.getenv("HNSW_EF_SEARCH", "60"))
# IVFFlat tuning
VECTOR_INDEX_TYPE = os.getenv("VECTOR_INDEX_TYPE", "hnsw").lower()  # 'hnsw' or 'ivfflat'
IVFFLAT_LISTS = int(os.getenv("IVFFLAT_LISTS", "100"))
IVFFLAT_PROBES = int(os.getenv("IVFFLAT_PROBES", "4"))

# Initialize model
model = SentenceTransformer('all-MiniLM-L6-v2')

async def encode_texts_async(texts: List[str], batch_size: int = 32):
    """Offload embedding computation to a thread to avoid blocking the event loop."""
    return await asyncio.to_thread(
        model.encode, texts, show_progress_bar=False, batch_size=batch_size
    )

# Database connection with validation
DB_URL = os.getenv("DATABASE_URL")

# Check if DATABASE_URL is a placeholder
def is_placeholder_url(url):
    """Check if DATABASE_URL is a placeholder value"""
    if not url:
        return False
    placeholder_indicators = [
        'host:port',  # Literal text "host:port"
        'user:password',  # Default placeholder
        '@host/',  # Generic host
        'your-',
        'example',
        '[', ']', '{', '}'
    ]
    for indicator in placeholder_indicators:
        if indicator.lower() in url.lower():
            return True
    return False

# Validate and fix DATABASE_URL
if DB_URL and is_placeholder_url(DB_URL):
    logger.error("DATABASE_URL is a placeholder value!")
    logger.error(f"Found: {DB_URL}")
    logger.error("Please set the actual DATABASE_URL in Render environment variables:")
    logger.error("postgresql://nexa_admin:h7L101QmZt1WTyVHrnm4rLOz2wKRVF4G@dpg-d3hh2i63jp1c73fht4hg-a:5432/nexa_aerh")
    logger.warning("Using in-memory storage until DATABASE_URL is fixed")
    DB_URL = None
elif DB_URL:
    # Fix missing port if needed
    parsed = urlparse(DB_URL)
    if not parsed.port and parsed.hostname:
        # Add default PostgreSQL port 5432
        netloc = f"{parsed.username}:{parsed.password}@{parsed.hostname}:5432" if parsed.username else f"{parsed.hostname}:5432"
        DB_URL = urlunparse((
            parsed.scheme,
            netloc,
            parsed.path,
            parsed.params,
            parsed.query,
            parsed.fragment
        ))
        logger.info("Fixed DATABASE_URL by adding port 5432")
    logger.info(f"DATABASE_URL configured: {DB_URL.split('@')[0].split('://')[0]}://***@{DB_URL.split('@')[1] if '@' in DB_URL else 'unknown'}")
else:
    logger.info("No DATABASE_URL configured, using in-memory storage")

# Attempt database connection with proper error handling
if DB_URL:
    try:
        logger.info(f"Attempting to connect to database...")
        # Mask password in log
        masked_url = DB_URL.split('@')[0].split('://')[0] + '://***@' + DB_URL.split('@')[1] if '@' in DB_URL else DB_URL
        logger.info(f"Connecting to: {masked_url}")
        
        conn = psycopg2.connect(DB_URL)
        cursor = conn.cursor()
        logger.info("Successfully connected to PostgreSQL database")
        
        # Create tables and vector index (HNSW with cosine ops)
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
        # Ensure ANN index exists with cosine ops for <=> queries (switchable: HNSW or IVFFlat)
        if VECTOR_INDEX_TYPE == "ivfflat":
            cursor.execute(f"""
                DO $$
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1 FROM pg_indexes WHERE indexname = 'spec_chunks_embedding_ivf_idx'
                    ) THEN
                        CREATE INDEX spec_chunks_embedding_ivf_idx
                        ON spec_chunks USING ivfflat (embedding vector_cosine_ops)
                        WITH (lists = {IVFFLAT_LISTS});
                    END IF;
                END
                $$;
            """)
        else:
            cursor.execute(f"""
                DO $$
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1 FROM pg_indexes WHERE indexname = 'spec_chunks_embedding_hnsw_idx'
                    ) THEN
                        CREATE INDEX spec_chunks_embedding_hnsw_idx
                        ON spec_chunks USING hnsw (embedding vector_cosine_ops)
                        WITH (m = {HNSW_M}, ef_construction = {HNSW_EF_CONSTRUCTION});
                    END IF;
                END
                $$;
            """)
        conn.commit()
        logger.info(f"Database initialized with {VECTOR_INDEX_TYPE} index")
        
    except psycopg2.ProgrammingError as e:
        logger.error(f"Database connection failed - ProgrammingError: {str(e)}")
        logger.warning("Falling back to in-memory storage")
        conn = None
        cursor = None
    except psycopg2.OperationalError as e:
        logger.error(f"Database connection failed - OperationalError: {str(e)}")
        logger.warning("Database may be unavailable. Falling back to in-memory storage")
        conn = None
        cursor = None
    except Exception as e:
        logger.error(f"Unexpected database connection error: {str(e)}")
        logger.warning("Falling back to in-memory storage")
        conn = None
        cursor = None
else:
    if DB_URL:
        logger.warning(f"DATABASE_URL is set but invalid: '{DB_URL[:50]}...' (truncated)")
        logger.warning("Please set a valid PostgreSQL connection string in Render.com environment variables")
        logger.warning("Format: postgresql://user:password@host:port/dbname")
    else:
        logger.info("No DATABASE_URL configured")
    
    logger.info("Using in-memory storage (no persistence between restarts)")
    conn = None
    cursor = None

# Global in-memory storage as fallback
memory_chunks = []
memory_embeddings = None
memory_index = None

# In-memory service metrics (basic)
metrics = {
    "learn_spec_count": 0,
    "learn_spec_last_ms": 0.0,
    "analyze_count": 0,
    "analyze_last_ms": 0.0,
    "analyze_avg_ms": 0.0,
    "knn_total_queries": 0,
    "knn_last_ms": 0.0,
    "knn_avg_ms": 0.0,
}

@lru_cache(maxsize=1024)
def clean_infraction_text(text):
    """Clean and normalize infraction text"""
    text = re.sub(r'\s+', ' ', text.strip())
    text = re.sub(r'([a-z])([A-Z])', r'\1 \2', text)
    text = re.sub(r'(\w)([.,;])', r'\1 \2', text)
    return text

def extract_text(pdf_path, chunk_size=500, batch_size=50):
    """Extract text from PDF with optimized chunking using pypdf.
    Honors MAX_PAGES and CHUNK_SIZE env configuration.
    """
    # Resolve effective params from env
    chunk_size = int(os.getenv("CHUNK_SIZE", str(chunk_size)))
    max_pages = int(os.getenv("MAX_PAGES", str(MAX_PAGES_DEFAULT)))

    reader = PdfReader(pdf_path)
    text_chunks = []
    
    for page_num, page in enumerate(reader.pages[:max_pages]):
        page_text = page.extract_text()
        if not page_text:
            continue
        
        # Chunk large pages
        for i in range(0, len(page_text), chunk_size):
            chunk = page_text[i:i+chunk_size]
            if chunk.strip():
                text_chunks.append({
                    'text': chunk,
                    'page': page_num + 1,
                    'source': os.path.basename(pdf_path)
                })
    
    return text_chunks

async def create_index_async(all_chunks, user_id):
    """Async variant: create embeddings and persist index. Uses pgvector when DB is present,
    otherwise builds an in-memory FAISS index.
    """
    global memory_chunks, memory_embeddings, memory_index

    texts = [c['text'] for c in all_chunks]
    embeddings = await encode_texts_async(texts, batch_size=32)

    # Create FAISS index (always useful for in-memory fallback)
    dimension = embeddings.shape[1]
    index = await asyncio.to_thread(lambda: faiss.IndexFlatL2(dimension))
    await asyncio.to_thread(index.add, embeddings.astype(np.float32))

    if cursor:
        # Persist to PostgreSQL with pgvector
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
            template="(%s, %s::vector, %s, %s)",
            page_size=1000
        )
        cursor.execute(
            "INSERT INTO audit_log (user_id, action, details) VALUES (%s, %s, %s)",
            (user_id, "learn_spec", json.dumps({"chunk_count": len(all_chunks)}))
        )
        conn.commit()

        # Dynamic IVFFlat lists tuning: rebuild IVF index sized to dataset
        if VECTOR_INDEX_TYPE == "ivfflat":
            N = len(all_chunks)
            lists = max(1, math.isqrt(N))
            # Recreate IVF index with tuned lists
            cursor.execute("DROP INDEX IF EXISTS spec_chunks_embedding_ivf_idx")
            cursor.execute(
                f"CREATE INDEX spec_chunks_embedding_ivf_idx ON spec_chunks USING ivfflat (embedding vector_cosine_ops) WITH (lists = {lists})"
            )
            cursor.execute("ANALYZE spec_chunks")
            conn.commit()
    else:
        # Keep in memory
        memory_chunks = all_chunks
        memory_embeddings = embeddings
        memory_index = index

    return index, embeddings

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
        t0 = time.time()
        all_chunks = []
        
        for spec_file in spec_files:
            # Validate file size
            size = getattr(spec_file, "size", None)
            if size and size > 50 * 1024 * 1024:
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
        
        # Create index from all chunks (async offload for embeddings)
        index, embeddings = await create_index_async(all_chunks, user_id)
        elapsed_ms = (time.time() - t0) * 1000.0
        metrics["learn_spec_count"] += 1
        metrics["learn_spec_last_ms"] = round(elapsed_ms, 2)
        logger.info(f"learn-spec: chunks={len(all_chunks)} elapsed_ms={elapsed_ms:.2f} index_type={VECTOR_INDEX_TYPE}")
        
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
    confidence_threshold: float = 0.7,
    probes: Optional[int] = None,
    ef_search: Optional[int] = None
):
    """Analyze an audit document for infractions"""
    try:
        t_all = time.time()
        # Validate file size
        size = getattr(audit_file, "size", None)
        if size and size > 50 * 1024 * 1024:
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
        
        # Analyze each infraction using pgvector (DB) or in-memory FAISS
        analysis = []
        per_query_ms = []
        if cursor:
            # Ensure we have a learned spec
            cursor.execute("SELECT COUNT(*) FROM spec_chunks")
            if cursor.fetchone()[0] == 0:
                os.remove(pdf_path)
                raise HTTPException(status_code=400, detail="No spec book loaded")

            # Set ANN search tuning per request (transaction-local)
            try:
                if VECTOR_INDEX_TYPE == "ivfflat":
                    effective_probes = IVFFLAT_PROBES if probes is None else int(probes)
                    cursor.execute("SET LOCAL ivfflat.probes = %s", (effective_probes,))
                else:
                    effective_ef = HNSW_EF_SEARCH if ef_search is None else int(ef_search)
                    cursor.execute("SET LOCAL hnsw.ef_search = %s", (effective_ef,))
            except Exception:
                pass

            for infraction in infractions:
                # Embed infraction without blocking loop
                inf_emb = (await encode_texts_async([infraction]))[0].astype(np.float32).tolist()
                # Top-5 nearest neighbors via pgvector
                tq = time.time()
                cursor.execute(
                    """
                    SELECT text, section_reference, source_file,
                           (embedding <=> %s::vector) AS distance
                    FROM spec_chunks
                    ORDER BY embedding <=> %s::vector ASC
                    LIMIT 5
                    """,
                    (inf_emb, inf_emb)
                )
                rows = cursor.fetchall()
                per_query_ms.append((time.time() - tq) * 1000.0)
                best_distance = rows[0][3] if rows else 1.0

                # Distance -> confidence mapping (same calibration as FAISS path)
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

                validity = confidence >= confidence_threshold
                repealable = not validity
                reasons = [r[0][:500] for r in rows[:3]] if rows else []
                spec_refs = [f"{r[2]} - {r[1]}" for r in rows[:3]] if rows else []

                analysis.append({
                    "infraction": infraction,
                    "validity": "YES" if validity else "NO",
                    "repealable": "YES" if repealable else "NO",
                    "confidence": round(float(confidence), 2),
                    "reasons": reasons,
                    "spec_refs": spec_refs,
                })
        else:
            # Use in-memory storage
            if memory_index is None:
                os.remove(pdf_path)
                raise HTTPException(status_code=400, detail="No spec book loaded")
            
            text_chunks = memory_chunks
            embeddings = memory_embeddings
            index = memory_index
            # Analyze each infraction with FAISS
            for infraction in infractions:
                tq = time.time()
                result = analyze_infraction(infraction, index, embeddings, text_chunks, confidence_threshold)
                per_query_ms.append((time.time() - tq) * 1000.0)
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
        elapsed_all_ms = (time.time() - t_all) * 1000.0
        # Update metrics
        metrics["analyze_count"] += 1
        metrics["analyze_last_ms"] = round(elapsed_all_ms, 2)
        # running avg
        prev = metrics["analyze_avg_ms"]
        n = metrics["analyze_count"]
        metrics["analyze_avg_ms"] = round(((prev * (n - 1)) + elapsed_all_ms) / n, 2)
        if per_query_ms:
            q_avg = sum(per_query_ms) / len(per_query_ms)
            metrics["knn_total_queries"] += len(per_query_ms)
            metrics["knn_last_ms"] = round(per_query_ms[-1], 2)
            prevq = metrics["knn_avg_ms"]
            m = metrics["knn_total_queries"]
            metrics["knn_avg_ms"] = round(((prevq * (m - len(per_query_ms))) + sum(per_query_ms)) / m, 2)
        logger.info(
            f"analyze-audit: infractions={total} elapsed_ms={elapsed_all_ms:.2f} index_type={VECTOR_INDEX_TYPE}"
        )
        
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

@app.get("/")
async def root():
    """Root endpoint - API information"""
    return {
        "service": "NEXA AI Document Analyzer API",
        "version": "1.0.0",
        "status": "running",
        "endpoints": {
            "health": "/health",
            "learn_spec": "/learn-spec/ (POST)",
            "analyze_audit": "/analyze-audit/ (POST)",
            "metrics": "/metrics",
            "benchmark": "/bench/knn"
        },
        "documentation": "/docs"
    }

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

# --- Monitoring Endpoints ---
@app.get("/metrics")
async def metrics_endpoint():
    """Return basic in-process metrics and configuration.
    Note: counters reset on process restart.
    """
    try:
        if cursor:
            cursor.execute("SELECT COUNT(*) FROM spec_chunks")
            chunk_count = cursor.fetchone()[0]
        else:
            chunk_count = len(memory_chunks) if memory_chunks else 0
    except Exception:
        chunk_count = None

    return {
        "service": "nexa-api",
        "vector_index_type": VECTOR_INDEX_TYPE,
        "defaults": {
            "ivfflat_lists": IVFFLAT_LISTS,
            "ivfflat_probes": IVFFLAT_PROBES,
            "hnsw_m": HNSW_M,
            "hnsw_ef_construction": HNSW_EF_CONSTRUCTION,
            "hnsw_ef_search": HNSW_EF_SEARCH,
        },
        "chunks_loaded": chunk_count,
        "metrics": metrics,
    }

@app.get("/db/pgstat")
async def db_pgstat():
    """Return top pg_stat_statements rows for embedding queries, if available."""
    if not cursor:
        return {"available": False, "reason": "No database connection"}
    try:
        cursor.execute(
            """
            SELECT query, calls, total_time, mean_time
            FROM pg_stat_statements
            WHERE query ILIKE '%embedding <=>%'
            ORDER BY total_time DESC
            LIMIT 5
            """
        )
        cols = [d[0] for d in cursor.description]
        rows = [dict(zip(cols, r)) for r in cursor.fetchall()]
        return {"available": True, "top": rows}
    except Exception as e:
        return {"available": False, "reason": str(e)}

@app.get("/bench/knn")
async def bench_knn(queries: int = 10, probes: Optional[int] = None, ef_search: Optional[int] = None):
    """Run a lightweight KNN benchmark using random spec chunks as queries.
    Returns avg/p50/p95 per-query times in ms.
    """
    if cursor:
        cursor.execute("SELECT COUNT(*) FROM spec_chunks")
        n = cursor.fetchone()[0]
        if n == 0:
            raise HTTPException(status_code=400, detail="No spec book loaded")
        cursor.execute("SELECT text FROM spec_chunks ORDER BY RANDOM() LIMIT %s", (queries,))
        samples = [r[0] for r in cursor.fetchall()]
        # Apply per-request tuning
        try:
            if VECTOR_INDEX_TYPE == "ivfflat":
                eff = IVFFLAT_PROBES if probes is None else int(probes)
                cursor.execute("SET LOCAL ivfflat.probes = %s", (eff,))
            else:
                eff = HNSW_EF_SEARCH if ef_search is None else int(ef_search)
                cursor.execute("SET LOCAL hnsw.ef_search = %s", (eff,))
        except Exception:
            pass
        times = []
        for text in samples:
            vec = (await encode_texts_async([text]))[0].astype(np.float32).tolist()
            tq = time.time()
            cursor.execute(
                """
                SELECT text, (embedding <=> %s::vector) AS distance
                FROM spec_chunks
                ORDER BY embedding <=> %s::vector ASC
                LIMIT 5
                """,
                (vec, vec)
            )
            _ = cursor.fetchall()
            times.append((time.time() - tq) * 1000.0)
    else:
        if not memory_chunks or memory_index is None:
            raise HTTPException(status_code=400, detail="No spec book loaded (memory)")
        # Memory FAISS path
        import random
        samples = [random.choice(memory_chunks)['text'] for _ in range(min(queries, len(memory_chunks)))]
        times = []
        for text in samples:
            tq = time.time()
            _ = analyze_infraction(text, memory_index, memory_embeddings, memory_chunks, 0.7)
            times.append((time.time() - tq) * 1000.0)

    times.sort()
    avg_ms = sum(times) / len(times)
    p50_ms = times[int(0.5 * (len(times)-1))]
    p95_ms = times[int(0.95 * (len(times)-1))]
    metrics["knn_last_ms"] = round(times[-1], 2)
    # Update running average across benchmarked queries
    metrics["knn_total_queries"] += len(times)
    prevq = metrics["knn_avg_ms"]
    m = metrics["knn_total_queries"]
    metrics["knn_avg_ms"] = round(((prevq * (m - len(times))) + sum(times)) / m, 2)

    return {
        "vector_index_type": VECTOR_INDEX_TYPE,
        "count": len(times),
        "avg_ms": round(avg_ms, 2),
        "p50_ms": round(p50_ms, 2),
        "p95_ms": round(p95_ms, 2),
    }
