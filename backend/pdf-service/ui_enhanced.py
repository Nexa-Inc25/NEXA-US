"""
NEXA AI Document Analyzer - Streamlit Frontend Service
Aligns with Phase 1-3 of NEXA Roadmap for AI-driven processing
"""

import streamlit as st
import os
import pickle
from sentence_transformers import SentenceTransformer
from pypdf import PdfReader
import nltk
import re
import torch
from datetime import datetime
import json
import numpy as np
import faiss
from sklearn.metrics.pairwise import cosine_similarity

# Page configuration MUST be the very first Streamlit command
st.set_page_config(
    page_title="NEXA AI Document Analyzer Enterprise",
    page_icon="■",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Download NLTK data (skip if already exists)
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt', quiet=True)

# Use lightweight model; check for GPU
device = 'cuda' if torch.cuda.is_available() else 'cpu'

# Handle model loading with retries and cache management
@st.cache_resource
def load_model():
    try:
        return SentenceTransformer('all-MiniLM-L6-v2', device=device)
    except Exception as e:
        st.warning(f"Model loading error: {e}. Retrying...")
        # Clear any lock files
        import shutil
        cache_dir = "/opt/render/.cache/torch/sentence_transformers"
        if os.path.exists(cache_dir):
            for file in os.listdir(cache_dir):
                if file.endswith(".lock"):
                    try:
                        os.remove(os.path.join(cache_dir, file))
                    except:
                        pass
        # Try again with fresh download
        return SentenceTransformer('all-MiniLM-L6-v2', device=device, cache_folder="/tmp/models")

model = load_model()

# Database connection (keep for future integration)
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:password@localhost/nexa_db")

# Environment and paths
ENV = os.getenv("ENV", "local")  # 'prod' for Pinecone, else FAISS
DATA_DIR = os.environ.get('RENDER_DISK_PATH', '/tmp') + '/data'
os.makedirs(DATA_DIR, exist_ok=True)

FAISS_INDEX_PATH = os.path.join(DATA_DIR, 'spec_index.faiss')
CHUNKS_PATH = os.path.join(DATA_DIR, 'spec_chunks.pkl')
EMBEDDINGS_PATH = os.path.join(DATA_DIR, 'spec_embeddings.npy')

# Custom CSS matching foreman app design
st.markdown("""
    <style>
    /* Global Styles */
    .main {
        background-color: #FFFFFF;
        padding-top: 0.5rem;
    }
    
    /* Headers */
    h1, h2, h3 {
        color: #2D3748 !important;
        font-weight: 700 !important;
    }
    
    h1 { font-size: 28px !important; }
    h2 { font-size: 20px !important; }
    h3 { font-size: 16px !important; }
    
    /* Buttons - Professional Steel Blue */
    .stButton>button {
        width: 100%;
        background-color: #4682B4;
        color: #FFFFFF;
        border-radius: 4px;
        font-weight: 700;
        font-size: 16px;
        padding: 12px 24px;
        transition: all 0.2s;
        border: none;
        box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05);
    }
    .stButton>button:hover {
        background-color: #5A7A9A;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
    }
    
    /* Metric Cards */
    [data-testid="stMetricValue"] {
        font-size: 24px;
        font-weight: 700;
        color: #4682B4;
    }
    [data-testid="stMetricLabel"] {
        font-size: 12px;
        color: #5A7A9A;
        font-weight: 500;
    }
    
    /* Tabs */
    .stTabs [data-baseweb="tab-list"] {
        background-color: #F8FAFC;
        border-bottom: 1px solid #E2E8F0;
    }
    .stTabs [data-baseweb="tab"] {
        color: #5A7A9A;
        font-weight: 500;
        font-size: 14px;
    }
    .stTabs [aria-selected="true"] {
        color: #4682B4;
        border-bottom-color: #4682B4;
    }
    
    /* File Uploader */
    [data-testid="stFileUploader"] {
        background-color: #F8FAFC;
        border: 1px solid #E2E8F0;
        border-radius: 4px;
        padding: 16px;
    }
    
    /* Dataframe - Foreman Style */
    [data-testid="stDataFrame"] {
        border: none;
        border-radius: 4px;
        overflow: hidden;
    }
    
    /* Job Cards - Foreman Style */
    .job-card {
        background-color: #F8FAFC;
        border-left: 4px solid #4682B4;
        padding: 16px;
        border-radius: 4px;
        margin-bottom: 8px;
        box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05);
    }
    .job-card-active { border-left-color: #4682B4; }
    .job-card-completed { border-left-color: #10B981; }
    .job-card-review { border-left-color: #F59E0B; }
    .job-card-pending { border-left-color: #9CA3AF; }
    
    /* Stat Cards - Foreman Style */
    .stat-card-container {
        display: flex;
        gap: 8px;
        margin: 16px 0;
    }
    .stat-card-item {
        flex: 1;
        background-color: #F8FAFC;
        padding: 16px;
        border-radius: 4px;
        text-align: center;
    }
    
    /* Success/Info/Warning - Subdued */
    .stSuccess, .stInfo, .stWarning, .stError {
        background-color: #F8FAFC;
        border-left: 4px solid;
        border-radius: 4px;
        padding: 12px;
        font-size: 14px;
        font-weight: 500;
    }
    .stSuccess { border-left-color: #10B981; color: #065F46; }
    .stInfo { border-left-color: #4682B4; color: #1E3A5F; }
    .stWarning { border-left-color: #F59E0B; color: #78350F; }
    .stError { border-left-color: #EF4444; color: #7F1D1D; }
    
    /* Sidebar */
    [data-testid="stSidebar"] {
        background-color: #F8FAFC;
        border-right: 1px solid #E2E8F0;
    }
    [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3 {
        color: #2D3748 !important;
    }
    
    /* Divider */
    hr {
        border-color: #E2E8F0;
    }
    </style>
""", unsafe_allow_html=True)

def extract_text_from_pdf(file):
    """Extract text from PDF file and return chunks"""
    reader = PdfReader(file)
    text = ''.join(page.extract_text() + '\n' for page in reader.pages)
    # Split by double newlines (paragraphs)
    chunks = [s.strip() for s in text.split('\n\n') if s.strip()]
    return chunks

def create_faiss_index(embeddings):
    """Create FAISS IVF index for efficient search"""
    dim = embeddings.shape[1]
    nlist = max(10, int(np.sqrt(len(embeddings))))  # Dynamic clustering
    quantizer = faiss.IndexFlatL2(dim)
    index = faiss.IndexIVFFlat(quantizer, dim, nlist)
    index.train(embeddings)
    index.add(embeddings)
    return index

def save_faiss_data(index, chunks, embeddings):
    """Save FAISS index and associated data"""
    faiss.write_index(index, FAISS_INDEX_PATH)
    with open(CHUNKS_PATH, 'wb') as f:
        pickle.dump(chunks, f)
    np.save(EMBEDDINGS_PATH, embeddings)

def load_faiss_data():
    """Load FAISS index and associated data"""
    if not os.path.exists(FAISS_INDEX_PATH):
        return None, None, None
    index = faiss.read_index(FAISS_INDEX_PATH)
    with open(CHUNKS_PATH, 'rb') as f:
        chunks = pickle.load(f)
    embeddings = np.load(EMBEDDINGS_PATH)
    return index, chunks, embeddings

@st.cache_resource
def process_spec_book(uploaded_file):
    """Process spec book with FAISS indexing"""
    chunks = extract_text_from_pdf(uploaded_file)
    
    # Generate embeddings
    embeddings = model.encode(chunks, show_progress_bar=True, batch_size=32, convert_to_numpy=True)
    
    # Create FAISS index
    index = create_faiss_index(embeddings)
    
    # Save to disk
    save_faiss_data(index, chunks, embeddings)
    
    return len(chunks)

def extract_infractions(chunks):
    """Extract infractions from audit chunks"""
    # Look for chunks that start with infraction markers
    patterns = ['infraction:', 'go-back', 'violation:', 'non-compliant']
    infractions = []
    
    for chunk in chunks:
        chunk_lower = chunk.lower()
        if any(pattern in chunk_lower for pattern in patterns):
            infractions.append(chunk)
    
    # If no specific infractions found, use all substantial chunks
    if not infractions:
        infractions = [c for c in chunks if len(c.strip()) > 50]
    
    return infractions

def analyze_audit_document(uploaded_file, confidence_threshold=0.7):
    """Analyze audit document using FAISS"""
    # Load FAISS index
    faiss_index, spec_chunks, spec_embeddings = load_faiss_data()
    if faiss_index is None:
        raise ValueError("Spec book not loaded. Please process spec book first.")
    
    # Extract infractions from audit
    audit_chunks = extract_text_from_pdf(uploaded_file)
    infractions = extract_infractions(audit_chunks)
    
    if not infractions:
        return []
    
    # Generate embeddings for infractions
    infraction_embeddings = model.encode(infractions, batch_size=16, convert_to_numpy=True)
    
    results = []
    for i, inf_emb in enumerate(infraction_embeddings):
        # Search FAISS index
        distances, indices = faiss_index.search(inf_emb.reshape(1, -1), k=5)
        
        # Calculate cosine similarities
        similarities = cosine_similarity(inf_emb.reshape(1, -1), spec_embeddings[indices[0]])[0]
        
        # Get max similarity
        max_similarity = max(similarities) if len(similarities) > 0 else 0.0
        
        # Determine if repealable
        can_repeal = max_similarity > confidence_threshold
        
        # Get relevant spec sections
        reasons = []
        spec_matches = 0
        for j, idx in enumerate(indices[0]):
            if similarities[j] > 0.6:
                spec_matches += 1
                if similarities[j] > 0.6 and can_repeal:
                    reason = f"Match ({similarities[j]:.0%}): {spec_chunks[idx][:150]}..."
                    reasons.append(reason)
        
        results.append({
            "infraction": infractions[i],
            "can_repeal": can_repeal,
            "confidence": float(max_similarity),
            "reasons": reasons[:3] if can_repeal else [],
            "spec_matches": spec_matches
        })
    
    return results

# UI Layout - Clean header
st.markdown("""
<div style="background-color: #F8FAFC; padding: 16px; border-bottom: 1px solid #E2E8F0; margin: -1rem -1rem 1rem -1rem;">
    <div style="margin-bottom: 8px;">
        <div style="font-size: 14px; color: #5A7A9A; font-weight: 400;">NEXA</div>
        <div style="font-size: 24px; font-weight: 700; color: #2D3748; margin-top: 4px;">AI Document Analyzer</div>
    </div>
    <div style="font-size: 14px; color: #5A7A9A; font-weight: 500;">{}</div>
</div>
""".format(datetime.now().strftime('%A, %B %d, %Y')), unsafe_allow_html=True)

# Sidebar - Professional metrics
with st.sidebar:
    st.header("System Configuration")
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Model", "MiniLM-L6-v2", delta="384-dim")
    with col2:
        st.metric("Device", device.upper(), delta="Ready")
    
    st.divider()
    st.subheader("Analysis Parameters")
    confidence_threshold = st.slider("Confidence Threshold", 0.0, 1.0, 0.7, 0.05)
    chunk_size = st.slider("Chunk Size", 200, 800, 400, 50)
    
    st.divider()
    st.info(f"**Embeddings Path:** {EMBEDDINGS_PATH}")
    
    # Offline mode indicator
    st.divider()
    if st.checkbox("Offline Mode"):
        st.warning("Offline: Uploads queued for sync")

# Main interface tabs - Clean labels
tab1, tab2, tab3 = st.tabs(["Learn Specification", "Analyze Audit", "Results"])

with tab1:
    st.header("Upload and Learn Spec Book")
    st.markdown("Upload your large spec book PDF (e.g., PG&E sections)")
    
    spec_file = st.file_uploader("Choose Spec Book PDF", type="pdf", key="spec_uploader")
    
    col1, col2 = st.columns([2, 1])
    with col1:
        if st.button("Process Specification Book", type="primary", use_container_width=True):
            if spec_file:
                with st.spinner("Processing spec book with FAISS indexing..."):
                    try:
                        num_chunks = process_spec_book(spec_file)
                        st.success(f"Successfully processed {num_chunks} chunks with FAISS index")
                        st.info(f"FAISS index saved to: {FAISS_INDEX_PATH}")
                    except Exception as e:
                        st.error(f"Error processing spec: {str(e)}")
            else:
                st.warning("Please upload a spec book first")
    
    with col2:
        if os.path.exists(FAISS_INDEX_PATH):
            st.success("Specification loaded")
            if st.button("Clear Cache"):
                try:
                    os.remove(FAISS_INDEX_PATH)
                    os.remove(CHUNKS_PATH)
                    os.remove(EMBEDDINGS_PATH)
                    st.rerun()
                except:
                    pass
        else:
            st.info("No spec loaded")

with tab2:
    st.header("Analyze QA Audit Document")
    st.markdown("Upload your QA audit document for infraction analysis")
    
    audit_file = st.file_uploader("Choose Audit PDF", type="pdf", key="audit_uploader")
    
    if st.button("Analyze Infractions", type="primary", use_container_width=True):
        if not os.path.exists(FAISS_INDEX_PATH):
            st.error("ERROR: Please load specification book first (Tab 1)")
        elif not audit_file:
            st.warning("Please upload an audit document")
        else:
            with st.spinner("Analyzing audit with FAISS vector search..."):
                try:
                    # Analyze using FAISS
                    analysis_results = analyze_audit_document(audit_file, confidence_threshold)
                    
                    if not analysis_results:
                        st.warning("No infractions found in audit document")
                    else:
                        # Format results for display
                        results = []
                        for result in analysis_results:
                            results.append({
                                "Infraction": result["infraction"][:150] + "..." if len(result["infraction"]) > 150 else result["infraction"],
                                "Status": "REPEALABLE" if result["can_repeal"] else "VALID",
                                "Confidence": f"{result['confidence']:.1%}",
                                "Spec Matches": result["spec_matches"],
                                "Primary Reason": result["reasons"][0] if result["reasons"] else "No spec match found"
                            })
                        
                        # Store results in session state
                        st.session_state['analysis_results'] = results
                        st.session_state['analysis_timestamp'] = datetime.now()
                        
                        st.success(f"Analysis complete: {len(results)} infractions processed with FAISS")
                    
                except Exception as e:
                    st.error(f"Analysis error: {str(e)}")
                    import traceback
                    st.code(traceback.format_exc())

with tab3:
    st.header("Analysis Results")
    
    if 'analysis_results' in st.session_state:
        results = st.session_state['analysis_results']
        timestamp = st.session_state['analysis_timestamp']
        
        # Summary metrics
        col1, col2, col3, col4 = st.columns(4)
        
        total_infractions = len(results)
        repealable = sum(1 for r in results if r["Status"] == "REPEALABLE")
        valid = total_infractions - repealable
        avg_confidence = np.mean([float(r["Confidence"].strip('%'))/100 for r in results])
        
        with col1:
            st.metric("Total Infractions", total_infractions)
        with col2:
            st.metric("Repealable", repealable, delta=f"-{repealable/total_infractions*100:.0f}%")
        with col3:
            st.metric("Valid", valid, delta=f"+{valid/total_infractions*100:.0f}%")
        with col4:
            st.metric("Avg Confidence", f"{avg_confidence:.1%}")
        
        st.divider()
        
        # Results table
        st.subheader("Detailed Analysis")
        
        # Filter options
        col1, col2 = st.columns(2)
        with col1:
            status_filter = st.selectbox("Filter by Status", ["All", "Repealable", "Valid"])
        with col2:
            sort_by = st.selectbox("Sort by", ["Confidence", "Status", "Spec Matches"])
        
        # Apply filters
        filtered_results = results
        if status_filter == "Repealable":
            filtered_results = [r for r in results if r["Status"] == "REPEALABLE"]
        elif status_filter == "Valid":
            filtered_results = [r for r in results if r["Status"] == "VALID"]
        
        # Sort results
        if sort_by == "Confidence":
            filtered_results = sorted(filtered_results, key=lambda x: float(x["Confidence"].strip('%')), reverse=True)
        elif sort_by == "Spec Matches":
            filtered_results = sorted(filtered_results, key=lambda x: x["Spec Matches"], reverse=True)
        
        # Display as job cards (foreman app style)
        for idx, r in enumerate(filtered_results):
            status_color = "#10B981" if r["Status"] == "VALID" else "#F59E0B"
            status_class = "job-card-completed" if r["Status"] == "VALID" else "job-card-review"
            
            st.markdown(f"""
            <div class="job-card {status_class}" style="border-left-color: {status_color};">
                <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 8px;">
                    <div style="flex: 1; margin-right: 8px;">
                        <div style="font-size: 16px; font-weight: 500; color: #2D3748; margin-bottom: 4px;">
                            {r['Infraction'][:100]}...
                        </div>
                    </div>
                    <div style="font-size: 14px; color: #5A7A9A; font-weight: 500;">{r['Confidence']}</div>
                </div>
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <div style="font-size: 14px; font-weight: 500; color: {status_color};">{r['Status']}</div>
                    <div style="font-size: 20px; color: #5A7A9A;">→</div>
                </div>
            </div>
            """, unsafe_allow_html=True)
        
        # Export options
        st.divider()
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("Export to JSON"):
                json_str = json.dumps(filtered_results, indent=2)
                st.download_button(
                    label="Download JSON",
                    data=json_str,
                    file_name=f"audit_analysis_{timestamp.strftime('%Y%m%d_%H%M%S')}.json",
                    mime="application/json"
                )
        
        with col2:
            if st.button("Generate Report"):
                report = f"""
NEXA AI Document Analysis Report
Generated: {timestamp.strftime('%Y-%m-%d %H:%M:%S')}

SUMMARY
-------
Total Infractions: {total_infractions}
Repealable: {repealable} ({repealable/total_infractions*100:.1f}%)
Valid: {valid} ({valid/total_infractions*100:.1f}%)
Average Confidence: {avg_confidence:.1%}

DETAILS
-------
"""
                for r in filtered_results:
                    report += f"\n{r['Status']}: {r['Infraction']}\n"
                    report += f"  Confidence: {r['Confidence']}\n"
                    report += f"  Reason: {r['Primary Reason']}\n"
                
                st.download_button(
                    label="Download Report",
                    data=report,
                    file_name=f"audit_report_{timestamp.strftime('%Y%m%d_%H%M%S')}.txt",
                    mime="text/plain"
                )
    else:
        st.info("No analysis results available. Please process an audit document in the Analyze tab.")

# Footer
st.divider()
st.markdown("""
<div style="text-align: center; color: #888; padding: 1rem;">
    <small>
    NEXA AI Document Analyzer v2.0 | Phase 1 Implementation<br>
    Powered by Sentence Transformers & PyPDF | Enterprise Edition
    </small>
</div>
""", unsafe_allow_html=True)
