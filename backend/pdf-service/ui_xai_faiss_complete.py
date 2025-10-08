"""
NEXA Document Intelligence - xAI + FAISS Complete Integration
Combines FAISS vector search for accurate spec retrieval with xAI analysis
"""
import streamlit as st
import PyPDF2
from io import BytesIO
import requests
import json
import os
import numpy as np
import faiss
import pickle
from sentence_transformers import SentenceTransformer
import hashlib
from datetime import datetime

# Configuration
XAI_API_KEY = os.environ.get('XAI_API_KEY')
USE_FAISS = True  # Toggle FAISS usage
CHUNK_SIZE = 1000  # Characters per chunk
CHUNK_OVERLAP = 200  # Overlap between chunks
TOP_K_RESULTS = 5  # Number of most relevant chunks to retrieve

st.set_page_config(
    page_title="NEXA Document Intelligence - FAISS",
    page_icon="🚧",
    layout="wide"
)

st.title("🚧 AI Document Analyzing Tool with FAISS")
st.markdown("**Enhanced with Vector Search for Accurate Spec Matching**")

# Initialize session state
if 'embeddings_model' not in st.session_state:
    st.session_state.embeddings_model = None
if 'faiss_index' not in st.session_state:
    st.session_state.faiss_index = None
if 'spec_chunks' not in st.session_state:
    st.session_state.spec_chunks = []
if 'analysis_cache' not in st.session_state:
    st.session_state.analysis_cache = {}

@st.cache_resource
def load_embedding_model():
    """Load Sentence-BERT model for embeddings"""
    try:
        model = SentenceTransformer('all-MiniLM-L6-v2')
        return model
    except Exception as e:
        st.error(f"Error loading embedding model: {e}")
        st.info("Install with: pip install sentence-transformers")
        return None

def chunk_text_smart(text, chunk_size=CHUNK_SIZE, overlap=CHUNK_OVERLAP):
    """
    Smart chunking that preserves context and section boundaries
    """
    chunks = []
    lines = text.split('\n')
    current_chunk = ""
    current_section = ""
    
    for line in lines:
        # Detect section headers (e.g., "Section 4.1.2", "4.1.2", etc.)
        if any(line.strip().startswith(f"{i}.") for i in range(1, 20)):
            # Save previous chunk if it exists
            if current_chunk and len(current_chunk) > 100:
                chunks.append({
                    'text': current_chunk.strip(),
                    'section': current_section,
                    'id': len(chunks)
                })
            # Start new chunk with section
            current_section = line.strip()[:50]  # First 50 chars of section header
            current_chunk = line + "\n"
        else:
            # Add to current chunk
            if len(current_chunk) + len(line) < chunk_size:
                current_chunk += line + "\n"
            else:
                # Save current chunk and start new one with overlap
                if current_chunk:
                    chunks.append({
                        'text': current_chunk.strip(),
                        'section': current_section,
                        'id': len(chunks)
                    })
                # Keep last part for context
                lines_in_chunk = current_chunk.split('\n')
                overlap_text = '\n'.join(lines_in_chunk[-3:]) if len(lines_in_chunk) > 3 else ""
                current_chunk = overlap_text + "\n" + line + "\n"
    
    # Add final chunk
    if current_chunk and len(current_chunk) > 100:
        chunks.append({
            'text': current_chunk.strip(),
            'section': current_section,
            'id': len(chunks)
        })
    
    return chunks

def create_faiss_index_from_chunks(chunks, model):
    """Create FAISS index from text chunks"""
    if not chunks or not model:
        return None, None
    
    # Extract texts
    texts = [chunk['text'] for chunk in chunks]
    
    # Generate embeddings
    with st.spinner(f"Generating embeddings for {len(chunks)} chunks..."):
        embeddings = model.encode(texts, show_progress_bar=True, batch_size=32)
    
    # Create FAISS index
    dimension = embeddings.shape[1]
    
    # Use IndexFlatIP for inner product (cosine similarity)
    index = faiss.IndexFlatIP(dimension)
    
    # Normalize for cosine similarity
    faiss.normalize_L2(embeddings)
    
    # Add vectors to index
    index.add(embeddings)
    
    st.success(f"✅ FAISS index created with {len(chunks)} chunks")
    return index, embeddings

def search_relevant_specs(query, index, chunks, model, k=TOP_K_RESULTS):
    """Search for most relevant specification chunks"""
    if not query or index is None or not chunks or not model:
        return []
    
    # Generate query embedding
    query_embedding = model.encode([query])
    faiss.normalize_L2(query_embedding)
    
    # Search in FAISS
    scores, indices = index.search(query_embedding, min(k, len(chunks)))
    
    # Prepare results
    results = []
    for score, idx in zip(scores[0], indices[0]):
        if idx < len(chunks):
            results.append({
                'chunk': chunks[idx],
                'score': float(score),
                'text': chunks[idx]['text'],
                'section': chunks[idx].get('section', 'Unknown')
            })
    
    return results

def analyze_with_faiss_context(infraction, relevant_chunks, spec_text_fallback):
    """Analyze infraction using FAISS-retrieved context"""
    
    # Prepare context from FAISS results
    if relevant_chunks:
        context = "\n\n".join([
            f"[Section: {r['section']} | Relevance: {r['score']:.2%}]\n{r['text'][:500]}"
            for r in relevant_chunks
        ])
        context_source = "FAISS Vector Search"
    else:
        # Fallback to truncated spec text
        context = spec_text_fallback[:10000]
        context_source = "Direct Text (FAISS unavailable)"
    
    # Create cache key
    cache_key = hashlib.md5(f"{infraction}{context[:500]}".encode()).hexdigest()
    
    # Check cache
    if cache_key in st.session_state.analysis_cache:
        return st.session_state.analysis_cache[cache_key]
    
    prompt = f"""
    You are a construction specification expert analyzing an audit infraction.
    
    SPECIFICATION CONTEXT (Source: {context_source}):
    {context}
    
    INFRACTION TO ANALYZE:
    {infraction}
    
    Analyze if this infraction is valid or can be appealed. Provide:
    
    1. VERDICT: Valid or Appealable
    2. CONFIDENCE: High/Medium/Low
    3. SPECIFICATION REFERENCE: Quote exact spec text that supports your verdict
    4. REASONING: Clear explanation based on the specification
    5. ACTION: Recommended action to take
    
    Format as:
    VERDICT: [Valid/Appealable]
    CONFIDENCE: [High/Medium/Low]
    SPEC REFERENCE: [Exact quote]
    REASONING: [Your explanation]
    ACTION: [Recommended action]
    """
    
    headers = {
        "Authorization": f"Bearer {XAI_API_KEY}",
        "Content-Type": "application/json"
    }
    
    data = {
        "model": "grok-beta",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.1,
        "max_tokens": 500
    }
    
    try:
        response = requests.post(
            "https://api.x.ai/v1/chat/completions",
            headers=headers,
            json=data,
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()["choices"][0]["message"]["content"]
            # Cache result
            st.session_state.analysis_cache[cache_key] = result
            return result
        else:
            return f"API Error: {response.status_code}"
    except Exception as e:
        return f"Error: {str(e)}"

# Main UI
col1, col2 = st.columns([1, 1])

with col1:
    st.header("📚 Upload Spec Book PDFs")
    spec_files = st.file_uploader(
        "Upload spec book PDFs (can be multiple)",
        type="pdf",
        accept_multiple_files=True
    )

with col2:
    st.header("📋 Upload Audit Document")
    audit_file = st.file_uploader(
        "Upload the audit document",
        type="pdf"
    )

# Process spec books
spec_text = ""
if spec_files:
    with st.spinner("Processing specification books..."):
        for spec_file in spec_files:
            pdf_reader = PyPDF2.PdfReader(BytesIO(spec_file.read()))
            for page in pdf_reader.pages:
                spec_text += page.extract_text() + "\n"
        
        st.success(f"✅ Spec book loaded: {len(spec_text):,} characters")
        
        # Create FAISS index if enabled
        if USE_FAISS:
            if st.session_state.embeddings_model is None:
                st.session_state.embeddings_model = load_embedding_model()
            
            if st.session_state.embeddings_model:
                # Chunk the spec text
                chunks = chunk_text_smart(spec_text)
                st.session_state.spec_chunks = chunks
                
                # Create FAISS index
                index, embeddings = create_faiss_index_from_chunks(
                    chunks, 
                    st.session_state.embeddings_model
                )
                st.session_state.faiss_index = index
                
                # Show statistics
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Total Chunks", len(chunks))
                with col2:
                    avg_chunk_size = sum(len(c['text']) for c in chunks) // len(chunks)
                    st.metric("Avg Chunk Size", f"{avg_chunk_size} chars")
                with col3:
                    sections = len(set(c.get('section', '') for c in chunks))
                    st.metric("Sections Found", sections)

# Process audit and analyze
if audit_file and spec_text:
    pdf_reader = PyPDF2.PdfReader(BytesIO(audit_file.read()))
    audit_text = ""
    for page in pdf_reader.pages:
        audit_text += page.extract_text() + "\n"
    
    st.success(f"✅ Audit document loaded: {len(audit_text):,} characters")
    
    # Analysis button
    if st.button("🔍 Analyze Infractions", type="primary"):
        # Extract infractions using xAI
        with st.spinner("Extracting infractions with AI..."):
            headers = {
                "Authorization": f"Bearer {XAI_API_KEY}",
                "Content-Type": "application/json"
            }
            
            extract_prompt = f"""
            You are an expert in extracting infractions from construction audit documents.
            Identify ALL infractions, violations, non-compliances, and go-back items.
            
            Output in JSON format:
            {{
              "infractions": [
                {{
                  "description": "Full description of the infraction",
                  "code": "Any code or ID (or null)",
                  "location": "Location/zone if mentioned (or null)",
                  "severity": "High/Medium/Low based on safety and cost impact"
                }}
              ]
            }}
            
            Audit text (truncated to 15000 chars):
            {audit_text[:15000]}
            """
            
            data = {
                "model": "grok-beta",
                "messages": [{"role": "user", "content": extract_prompt}],
                "temperature": 0.1
            }
            
            try:
                response = requests.post(
                    "https://api.x.ai/v1/chat/completions",
                    headers=headers,
                    json=data,
                    timeout=30
                )
                
                # Parse response
                extracted_text = response.json()["choices"][0]["message"]["content"]
                
                # Try to extract JSON
                import re
                json_match = re.search(r'\{.*\}', extracted_text, re.DOTALL)
                if json_match:
                    extracted = json.loads(json_match.group())
                else:
                    extracted = json.loads(extracted_text)
                
                infractions = extracted.get('infractions', [])
                
                if not infractions:
                    st.info("No infractions found in the audit document.")
                else:
                    st.subheader(f"🚨 Found {len(infractions)} Infractions")
                    
                    # Analyze each infraction
                    for i, inf in enumerate(infractions, 1):
                        severity_icon = {
                            'High': '🔴',
                            'Medium': '🟡', 
                            'Low': '🟢'
                        }.get(inf.get('severity', 'Medium'), '⚪')
                        
                        with st.expander(f"{severity_icon} Infraction {i}: {inf['description'][:80]}..."):
                            # Display infraction details
                            col1, col2 = st.columns([2, 1])
                            
                            with col1:
                                st.write(f"**Description:** {inf['description']}")
                                if inf.get('code'):
                                    st.write(f"**Code:** {inf['code']}")
                                if inf.get('location'):
                                    st.write(f"**Location:** {inf['location']}")
                            
                            with col2:
                                st.write(f"**Severity:** {inf.get('severity', 'Unknown')}")
                            
                            # FAISS search for relevant specs
                            relevant_specs = []
                            if USE_FAISS and st.session_state.faiss_index is not None:
                                with st.spinner("Searching specifications..."):
                                    relevant_specs = search_relevant_specs(
                                        inf['description'],
                                        st.session_state.faiss_index,
                                        st.session_state.spec_chunks,
                                        st.session_state.embeddings_model,
                                        k=3
                                    )
                                
                                if relevant_specs:
                                    st.markdown("### 📖 Relevant Spec Sections (via FAISS)")
                                    for j, spec in enumerate(relevant_specs, 1):
                                        st.write(f"**{j}. {spec['section']}** (Relevance: {spec['score']:.1%})")
                                        st.write(f"   {spec['text'][:200]}...")
                            
                            # Analyze with xAI
                            with st.spinner("Analyzing against specifications..."):
                                analysis = analyze_with_faiss_context(
                                    inf['description'],
                                    relevant_specs,
                                    spec_text
                                )
                                
                                st.markdown("### 🔬 Analysis Result")
                                
                                # Parse and display structured result
                                if "VERDICT:" in analysis:
                                    lines = analysis.split('\n')
                                    for line in lines:
                                        if line.strip():
                                            if "VERDICT:" in line and "Appealable" in line:
                                                st.success(line)
                                            elif "VERDICT:" in line and "Valid" in line:
                                                st.error(line)
                                            elif "CONFIDENCE:" in line:
                                                st.info(line)
                                            else:
                                                st.write(line)
                                else:
                                    st.write(analysis)
                    
                    # Summary statistics
                    st.markdown("---")
                    st.markdown("### 📊 Summary")
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Total Infractions", len(infractions))
                    with col2:
                        high_severity = sum(1 for inf in infractions if inf.get('severity') == 'High')
                        st.metric("High Severity", high_severity)
                    with col3:
                        if USE_FAISS and st.session_state.faiss_index:
                            st.metric("FAISS Status", "✅ Active")
                        else:
                            st.metric("FAISS Status", "❌ Inactive")
                            
            except Exception as e:
                st.error(f"Error in analysis: {str(e)}")
                st.info("Please check your xAI API key and try again.")

else:
    if not spec_text:
        st.info("👈 Please upload specification book PDFs first")
    elif not audit_file:
        st.info("👈 Please upload an audit document")

# Sidebar information
st.sidebar.header("🚀 System Configuration")

# FAISS toggle
use_faiss = st.sidebar.checkbox("Use FAISS Vector Search", value=USE_FAISS)
if use_faiss != USE_FAISS:
    st.experimental_rerun()

st.sidebar.markdown("---")
st.sidebar.header("📊 Performance Metrics")

if st.session_state.faiss_index:
    st.sidebar.success("✅ FAISS Index Loaded")
    st.sidebar.metric("Indexed Chunks", len(st.session_state.spec_chunks))
else:
    st.sidebar.warning("⚠️ FAISS Index Not Created")

if st.session_state.analysis_cache:
    st.sidebar.metric("Cached Analyses", len(st.session_state.analysis_cache))

# Deployment instructions
st.sidebar.markdown("---")
st.sidebar.header("📦 Requirements")
st.sidebar.code("""
streamlit
PyPDF2
requests
sentence-transformers
faiss-cpu
numpy
""")

st.sidebar.markdown("---")
st.sidebar.header("🌍 Environment Variables")
st.sidebar.code("XAI_API_KEY=your_key_here")

# Benefits of FAISS
with st.sidebar.expander("🎯 Why FAISS?"):
    st.markdown("""
    **FAISS Benefits:**
    - **Accuracy**: Finds most relevant spec sections
    - **Speed**: Sub-second search in large documents
    - **Context**: Better context for xAI analysis
    - **Cost**: Reduces API tokens by sending only relevant sections
    
    **Without FAISS:**
    - Sends first 15k chars of spec (may miss relevant parts)
    - Higher API costs
    - Less accurate analysis
    
    **With FAISS:**
    - Sends top 3-5 most relevant sections
    - Lower API costs
    - More accurate verdicts
    """)

# Check API key
if not XAI_API_KEY:
    st.error("⚠️ XAI_API_KEY not set. Please configure in environment variables.")
    st.stop()
