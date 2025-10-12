"""
NEXA AI Document Analyzer - Production Ready
FastAPI + Streamlit UI with optimized PDF extraction
Configured for Render Pro plan ($30/month, 2 CPU, 4GB RAM)
"""

import streamlit as st
import requests
import json
import pandas as pd
from fastapi import FastAPI, UploadFile, File, HTTPException, Depends
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import fitz  # PyMuPDF
from sentence_transformers import SentenceTransformer
import faiss
import numpy as np
import psycopg2
from psycopg2.extras import execute_values
import os
import re
import asyncio
from concurrent.futures import ThreadPoolExecutor
import threading
import uvicorn
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# FastAPI app
app = FastAPI(title="NEXA AI Document Analyzer")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize model
model = SentenceTransformer('all-MiniLM-L6-v2')

# Database configuration
DB_URL = os.getenv("DATABASE_URL", "postgresql://user:pass@localhost/nexa")
USE_POSTGRES = os.getenv("USE_POSTGRES", "false").lower() == "true"

# Optimized regex patterns from our development
BULLET_REGEX = r'[·•\-\*]\s*([A-Z][A-Z\s&]+?)(?:\s*[-–—]\s*|\n(?=[·•\-\*])|$)'
NUMBERED_REGEX = r'(\d+)\.\s*([^\n]+(?:\n\s+[^\n\d]+)*)'
INFRACTION_REGEX = r'(?i)(go-back|infraction|violation|issue|problem|deficiency|non-compliance):\s*([^\n]+(?:\n(?!(?:go-back|infraction|violation|issue|problem|deficiency|non-compliance):)[^\n]+)*)'

# Global storage (in-memory for non-Postgres deployments)
spec_index = None
spec_chunks = []
spec_embeddings = None

# PostgreSQL connection (if enabled)
if USE_POSTGRES:
    try:
        conn = psycopg2.connect(DB_URL)
        cursor = conn.cursor()
        
        # Create table with pgvector extension
        cursor.execute("""
            CREATE EXTENSION IF NOT EXISTS vector;
            CREATE TABLE IF NOT EXISTS spec_chunks (
                id SERIAL PRIMARY KEY,
                text TEXT,
                embedding vector(384),
                section_reference VARCHAR(100),
                page_number INT
            )
        """)
        conn.commit()
        logger.info("PostgreSQL connected with pgvector")
    except Exception as e:
        logger.warning(f"PostgreSQL connection failed: {e}. Using in-memory storage.")
        USE_POSTGRES = False

# Extract text from PDF with optimized chunking
def extract_text_chunked(pdf_path, chunk_size=5000, batch_size=50):
    """Extract text from PDF with smart chunking"""
    doc = fitz.open(pdf_path)
    text_chunks = []
    
    for batch_start in range(0, doc.page_count, batch_size):
        batch_end = min(batch_start + batch_size, doc.page_count)
        
        for page_num in range(batch_start, batch_end):
            page = doc[page_num]
            page_text = page.get_text("text")
            
            # Chunk large pages
            if len(page_text) > chunk_size:
                for i in range(0, len(page_text), chunk_size):
                    chunk = page_text[i:i+chunk_size]
                    text_chunks.append({
                        'text': chunk,
                        'page': page_num + 1,
                        'section': f"Page {page_num + 1}, Part {i//chunk_size + 1}"
                    })
            elif page_text.strip():
                text_chunks.append({
                    'text': page_text,
                    'page': page_num + 1,
                    'section': f"Page {page_num + 1}"
                })
    
    doc.close()
    return text_chunks

# Extract required documents dynamically
def extract_required_docs(text):
    """Extract AS-BUILT ORDER or similar document lists"""
    required_docs = []
    
    # Look for AS-BUILT ORDER section
    if "AS-BUILT ORDER" in text.upper() or "REQUIRED DOCUMENTS" in text.upper():
        section_match = re.search(
            r'(?:AS[\-\s]?BUILT ORDER|REQUIRED DOCUMENTS)[:\s]*(.*?)(?=\n[A-Z]{4,}|\n\n\n|\Z)',
            text,
            re.IGNORECASE | re.DOTALL
        )
        
        if section_match:
            section_text = section_match.group(1)
            
            # Extract bullet items
            bullets = re.findall(BULLET_REGEX, section_text, re.MULTILINE)
            for bullet in bullets:
                doc_name = bullet.strip()
                if doc_name and len(doc_name) > 2:
                    required_docs.append(doc_name)
            
            # Extract numbered items
            numbered = re.findall(NUMBERED_REGEX, section_text, re.MULTILINE)
            for num, item in numbered:
                doc_name = item.strip().split(' - ')[0] if ' - ' in item else item.strip()
                if doc_name and len(doc_name) > 2:
                    required_docs.append(doc_name)
    
    # Fallback to default list if extraction failed
    if not required_docs:
        required_docs = [
            'POLE BILL', 'EC TAG', 'PG&E FACE SHEET',
            'EQUIPMENT & POLE INFORMATION', 'CONSTRUCTION FEEDBACK',
            'CREW INSTRUCTIONS', 'CREW MATERIALS', 'MAP',
            'JP FORMS', 'CCSC'
        ]
    
    return required_docs

# Extract infractions with optimized regex
def extract_infractions(text):
    """Extract infractions using optimized multi-line regex"""
    infractions = []
    
    # Primary pattern for multi-line infractions
    matches = re.findall(INFRACTION_REGEX, text, re.MULTILINE | re.DOTALL)
    
    for match in matches:
        if isinstance(match, tuple) and len(match) >= 2:
            infraction_type = match[0]
            description = match[1].strip()
            # Clean multi-line description
            description = re.sub(r'\s*\n\s*', ' ', description)
            description = re.sub(r'\s+', ' ', description)
            
            infraction = f"{infraction_type}: {description}"
            if len(infraction) > 20 and len(infraction) < 1000:
                infractions.append(infraction)
    
    # Secondary patterns
    secondary_patterns = [
        r'(?i)\b(failed to|missing|incorrect|improper)\b\s*([^.!?\n]{10,200})',
        r'(?i)(?:item\s*\d+[:\.]?\s*)(.*?(?:violation|infraction|issue)[^.!?\n]*)'
    ]
    
    for pattern in secondary_patterns:
        matches = re.findall(pattern, text, re.MULTILINE)
        for match in matches:
            if isinstance(match, tuple):
                infraction = f"{match[0]}: {match[1].strip()}" if len(match) > 1 else match[0]
                if len(infraction) > 20 and len(infraction) < 1000 and infraction not in infractions:
                    infractions.append(infraction)
    
    return infractions

# Create FAISS index
def create_index(text_chunks):
    """Create FAISS index and optionally store in PostgreSQL"""
    global spec_index, spec_chunks, spec_embeddings
    
    # Extract just the text for encoding
    texts = [chunk['text'] for chunk in text_chunks]
    
    # Create embeddings
    logger.info(f"Creating embeddings for {len(texts)} chunks...")
    embeddings = model.encode(texts, show_progress_bar=False, batch_size=32)
    
    # Create FAISS index
    dimension = embeddings.shape[1]
    spec_index = faiss.IndexFlatL2(dimension)
    spec_index.add(embeddings.astype(np.float32))
    
    # Store globally
    spec_chunks = text_chunks
    spec_embeddings = embeddings
    
    # Store in PostgreSQL if enabled
    if USE_POSTGRES:
        try:
            cursor.execute("TRUNCATE TABLE spec_chunks")
            data = [
                (
                    chunk['text'],
                    embedding.tolist(),
                    chunk['section'],
                    chunk['page']
                )
                for chunk, embedding in zip(text_chunks, embeddings)
            ]
            execute_values(
                cursor,
                "INSERT INTO spec_chunks (text, embedding, section_reference, page_number) VALUES %s",
                data,
                template="(%s, %s::vector, %s, %s)"
            )
            conn.commit()
            logger.info(f"Stored {len(text_chunks)} chunks in PostgreSQL")
        except Exception as e:
            logger.error(f"Failed to store in PostgreSQL: {e}")
    
    return spec_index, embeddings

# Load index from PostgreSQL
def load_index_from_db():
    """Load spec chunks and index from PostgreSQL"""
    global spec_index, spec_chunks, spec_embeddings
    
    if not USE_POSTGRES:
        return False
    
    try:
        cursor.execute("SELECT text, embedding, section_reference, page_number FROM spec_chunks")
        rows = cursor.fetchall()
        
        if not rows:
            return False
        
        spec_chunks = [
            {'text': row[0], 'section': row[2], 'page': row[3]}
            for row in rows
        ]
        spec_embeddings = np.array([row[1] for row in rows], dtype=np.float32)
        
        # Recreate FAISS index
        spec_index = faiss.IndexFlatL2(spec_embeddings.shape[1])
        spec_index.add(spec_embeddings)
        
        logger.info(f"Loaded {len(spec_chunks)} chunks from PostgreSQL")
        return True
    except Exception as e:
        logger.error(f"Failed to load from PostgreSQL: {e}")
        return False

# Analyze infraction against spec
def analyze_infraction(infraction):
    """Analyze a single infraction against the spec index"""
    if spec_index is None or not spec_chunks:
        return {
            "infraction": infraction,
            "repealable": False,
            "confidence": 0.0,
            "reasons": ["No specification loaded"]
        }
    
    # Encode infraction
    infraction_embedding = model.encode([infraction])[0].astype(np.float32)
    
    # Search in index
    k = min(5, spec_index.ntotal)
    distances, indices = spec_index.search(np.array([infraction_embedding]), k)
    
    # Calculate confidence (convert L2 distance to percentage)
    best_distance = distances[0][0] if distances.shape[1] > 0 else float('inf')
    
    if best_distance < 0.3:
        confidence = 95.0
    elif best_distance < 0.5:
        confidence = 85.0
    elif best_distance < 0.7:
        confidence = 70.0
    elif best_distance < 1.0:
        confidence = 55.0
    elif best_distance < 1.5:
        confidence = 40.0
    else:
        confidence = 20.0
    
    # Determine repealability
    repealable = confidence > 50
    
    # Get matching spec sections as reasons
    reasons = []
    for idx, dist in zip(indices[0], distances[0]):
        if dist < 1.0 and idx < len(spec_chunks):
            chunk = spec_chunks[idx]
            reason_text = chunk['text'][:200] + "..." if len(chunk['text']) > 200 else chunk['text']
            reasons.append(f"{chunk['section']}: {reason_text}")
    
    return {
        "infraction": infraction,
        "repealable": repealable,
        "confidence": float(confidence),
        "reasons": reasons[:3]  # Top 3 reasons
    }

# FastAPI endpoints
@app.post("/learn-spec/")
async def learn_spec(spec_file: UploadFile = File(...)):
    """Process and learn from a specification book"""
    try:
        # Save uploaded file temporarily
        pdf_path = f"/tmp/{spec_file.filename}"
        with open(pdf_path, "wb") as f:
            content = await spec_file.read()
            f.write(content)
        
        # Extract text with chunking
        text_chunks = extract_text_chunked(pdf_path)
        
        if not text_chunks:
            raise HTTPException(status_code=400, detail="No text extracted from PDF")
        
        # Create index
        index, embeddings = create_index(text_chunks)
        
        # Clean up
        os.remove(pdf_path)
        
        return {
            "success": True,
            "index_size": index.ntotal,
            "embedding_dim": embeddings.shape[1],
            "total_chunks": len(text_chunks),
            "message": f"Learned {len(text_chunks)} chunks from specification"
        }
    except Exception as e:
        logger.error(f"Error learning spec: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/analyze-audit/")
async def analyze_audit(audit_file: UploadFile = File(...)):
    """Analyze an audit document for infractions"""
    try:
        # Check if index is loaded
        if spec_index is None:
            # Try to load from database
            if not load_index_from_db():
                raise HTTPException(status_code=400, detail="No specification loaded. Please upload a spec book first.")
        
        # Save uploaded file temporarily
        pdf_path = f"/tmp/{audit_file.filename}"
        with open(pdf_path, "wb") as f:
            content = await audit_file.read()
            f.write(content)
        
        # Extract text
        doc = fitz.open(pdf_path)
        audit_text = ""
        for page in doc:
            audit_text += page.get_text("text") + "\n"
        doc.close()
        
        # Extract infractions
        infractions = extract_infractions(audit_text)
        
        if not infractions:
            # Try simpler extraction
            infractions = re.findall(r'(?i)(?:issue|problem|violation):\s*([^\n]+)', audit_text)
        
        # Analyze each infraction
        analysis = [analyze_infraction(inf) for inf in infractions]
        
        # Summary statistics
        total = len(analysis)
        repealable = sum(1 for a in analysis if a['repealable'])
        avg_confidence = np.mean([a['confidence'] for a in analysis]) if analysis else 0
        
        # Clean up
        os.remove(pdf_path)
        
        return {
            "success": True,
            "summary": {
                "total_infractions": total,
                "repealable_count": repealable,
                "non_repealable_count": total - repealable,
                "average_confidence": round(avg_confidence, 2)
            },
            "analysis": analysis
        }
    except Exception as e:
        logger.error(f"Error analyzing audit: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "pdf-processor",
        "index_loaded": spec_index is not None,
        "chunks_loaded": len(spec_chunks),
        "postgres_enabled": USE_POSTGRES
    }

# Streamlit UI
def run_streamlit():
    """Run the Streamlit UI"""
    st.set_page_config(
        page_title="NEXA AI Document Analyzer",
        page_icon="📄",
        layout="wide"
    )
    
    # Custom styling
    st.markdown("""
    <style>
    .main {background-color: #f0f2f6;}
    .stButton>button {
        background-color: #00d4ff;
        color: white;
        font-weight: bold;
    }
    </style>
    """, unsafe_allow_html=True)
    
    st.sidebar.title("🔍 NEXA AI Analyzer")
    page = st.sidebar.radio("Navigation", ["📚 Learn Spec", "🔍 Analyze Audit", "📊 Results"])
    
    API_URL = os.getenv("API_URL", "http://localhost:8000")
    
    if page == "📚 Learn Spec":
        st.header("📚 Upload Specification Book")
        st.markdown("Upload a PDF specification book to create a searchable knowledge base.")
        
        spec_file = st.file_uploader("Choose a spec book PDF", type="pdf")
        if spec_file:
            col1, col2 = st.columns(2)
            with col1:
                st.info(f"📄 File: {spec_file.name}")
                st.info(f"📏 Size: {spec_file.size / 1024 / 1024:.1f} MB")
            
            if st.button("🚀 Learn Specification", type="primary"):
                with st.spinner("Processing spec book... This may take a few minutes."):
                    try:
                        files = {"spec_file": (spec_file.name, spec_file.getvalue(), "application/pdf")}
                        response = requests.post(f"{API_URL}/learn-spec/", files=files, timeout=300)
                        
                        if response.status_code == 200:
                            result = response.json()
                            st.success(f"✅ Spec book learned successfully!")
                            
                            col1, col2, col3 = st.columns(3)
                            col1.metric("Total Chunks", result['total_chunks'])
                            col2.metric("Index Size", result['index_size'])
                            col3.metric("Embedding Dim", result['embedding_dim'])
                            
                            st.info(result.get('message', 'Processing complete'))
                        else:
                            st.error(f"Failed: {response.text}")
                    except Exception as e:
                        st.error(f"Error: {str(e)}")
    
    elif page == "🔍 Analyze Audit":
        st.header("🔍 Analyze Audit Document")
        st.markdown("Upload an audit PDF to find infractions and determine repealability.")
        
        audit_file = st.file_uploader("Choose an audit PDF", type="pdf")
        if audit_file:
            st.info(f"📄 File: {audit_file.name} ({audit_file.size / 1024 / 1024:.1f} MB)")
            
            if st.button("🔍 Analyze Audit", type="primary"):
                with st.spinner("Analyzing audit document..."):
                    try:
                        files = {"audit_file": (audit_file.name, audit_file.getvalue(), "application/pdf")}
                        response = requests.post(f"{API_URL}/analyze-audit/", files=files, timeout=300)
                        
                        if response.status_code == 200:
                            result = response.json()
                            st.success("✅ Analysis complete!")
                            
                            # Summary metrics
                            summary = result.get('summary', {})
                            col1, col2, col3, col4 = st.columns(4)
                            col1.metric("Total Infractions", summary.get('total_infractions', 0))
                            col2.metric("Repealable", summary.get('repealable_count', 0))
                            col3.metric("Non-Repealable", summary.get('non_repealable_count', 0))
                            col4.metric("Avg Confidence", f"{summary.get('average_confidence', 0):.1f}%")
                            
                            # Detailed results
                            st.subheader("Detailed Analysis")
                            analysis = result.get('analysis', [])
                            
                            if analysis:
                                # Create DataFrame
                                df = pd.DataFrame(analysis)
                                
                                # Display each infraction
                                for i, item in enumerate(analysis, 1):
                                    with st.expander(f"Infraction {i}: {item['infraction'][:50]}..."):
                                        col1, col2 = st.columns([1, 3])
                                        with col1:
                                            if item['repealable']:
                                                st.success("✅ REPEALABLE")
                                            else:
                                                st.error("❌ NOT REPEALABLE")
                                            st.metric("Confidence", f"{item['confidence']:.1f}%")
                                        with col2:
                                            st.markdown("**Reasons from Spec:**")
                                            for reason in item['reasons']:
                                                st.write(f"• {reason}")
                                
                                # Download button
                                st.download_button(
                                    label="📥 Download Results (JSON)",
                                    data=json.dumps(result, indent=2),
                                    file_name=f"audit_analysis_{audit_file.name}.json",
                                    mime="application/json"
                                )
                            else:
                                st.warning("No infractions found in the document.")
                        else:
                            st.error(f"Analysis failed: {response.text}")
                    except Exception as e:
                        st.error(f"Error: {str(e)}")
    
    elif page == "📊 Results":
        st.header("📊 Analysis Results")
        st.info("Previous analysis results will appear here after processing an audit.")
        
        # Check service health
        try:
            response = requests.get(f"{API_URL}/health")
            if response.status_code == 200:
                health = response.json()
                st.sidebar.success("✅ Service Online")
                st.sidebar.info(f"Index Loaded: {health.get('index_loaded', False)}")
                st.sidebar.info(f"Chunks: {health.get('chunks_loaded', 0)}")
        except:
            st.sidebar.error("❌ Service Offline")

# Main execution
if __name__ == "__main__":
    # Run both FastAPI and Streamlit
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "streamlit":
        # Run Streamlit only
        run_streamlit()
    elif len(sys.argv) > 1 and sys.argv[1] == "fastapi":
        # Run FastAPI only
        uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 8000)))
    else:
        # Run both in threads (for development)
        # In production, use separate processes or containers
        api_thread = threading.Thread(
            target=lambda: uvicorn.run(app, host="0.0.0.0", port=8000)
        )
        api_thread.daemon = True
        api_thread.start()
        
        # Give API time to start
        import time
        time.sleep(2)
        
        # Run Streamlit in main thread
        run_streamlit()
