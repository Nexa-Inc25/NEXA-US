"""
NEXA AI Document Analyzer - Streamlit Frontend Service
Aligns with Phase 1-3 of NEXA Roadmap for AI-driven processing
"""

import streamlit as st
import os
import pickle
from sentence_transformers import SentenceTransformer, util
from pypdf import PdfReader
import nltk
import re
import torch
import psycopg2
from datetime import datetime
import json
import numpy as np

# Download NLTK data (skip if already exists)
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt', quiet=True)

# Use lightweight model; check for GPU
device = 'cuda' if torch.cuda.is_available() else 'cpu'
model = SentenceTransformer('all-MiniLM-L6-v2', device=device)

# Database connection (keep for future integration)
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:password@localhost/nexa_db")

# Persistence (attach Render Disk for production; fallback to temp)
EMBEDDINGS_PATH = os.environ.get('RENDER_DISK_PATH', '/tmp') + '/spec_embeddings.pkl'

# Page configuration
st.set_page_config(
    page_title="NEXA AI Document Analyzer Enterprise",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for professional styling
st.markdown("""
    <style>
    .main {
        padding-top: 1rem;
    }
    .stButton>button {
        width: 100%;
        background-color: #4682B4;
        color: white;
        border-radius: 8px;
        font-weight: bold;
        transition: all 0.3s;
        border: none;
    }
    .stButton>button:hover {
        background-color: #5A7A9A;
        box-shadow: 0 4px 12px rgba(70, 130, 180, 0.3);
    }
    .metric-card {
        background-color: #f8fafc;
        padding: 1rem;
        border-radius: 8px;
        border-left: 4px solid #4682B4;
    }
    </style>
""", unsafe_allow_html=True)

def extract_text_from_pdf(file):
    """Extract text from PDF file"""
    reader = PdfReader(file)
    return ''.join(page.extract_text() + '\n' for page in reader.pages)

def chunk_text(text, chunk_size=400):
    """Chunk text for efficient embedding"""
    sentences = nltk.sent_tokenize(text)
    chunks, current = [], ''
    for sent in sentences:
        if len(current) + len(sent) > chunk_size:
            chunks.append(current.strip())
            current = sent
        else:
            current += ' ' + sent
    if current: 
        chunks.append(current.strip())
    return chunks

@st.cache_resource
def load_or_learn_spec(uploaded_file):
    """Cache spec embeddings for performance"""
    if os.path.exists(EMBEDDINGS_PATH):
        with open(EMBEDDINGS_PATH, 'rb') as f:
            return pickle.load(f)
    
    text = extract_text_from_pdf(uploaded_file)
    chunks = chunk_text(text)
    
    # Batch encode for large specs
    embeddings = model.encode(chunks, show_progress_bar=True, batch_size=32)
    
    # Save to disk
    os.makedirs(os.path.dirname(EMBEDDINGS_PATH), exist_ok=True)
    with open(EMBEDDINGS_PATH, 'wb') as f:
        pickle.dump((chunks, embeddings), f)
    
    return chunks, embeddings

def extract_go_back_infractions(audit_text):
    """Extract go-back infractions from audit text"""
    # Regex for "go-back" infractions; customize if format varies
    patterns = [
        r'(go-back.*?)(?=\n\n|\Z|go-back)',
        r'(infraction:.*?)(?=\n\n|\Z|infraction:)',
        r'(violation:.*?)(?=\n\n|\Z|violation:)'
    ]
    
    infractions = []
    for pattern in patterns:
        infractions.extend(re.findall(pattern, audit_text, re.IGNORECASE | re.DOTALL))
    
    return infractions if infractions else audit_text.split('\n')[:20]  # Fallback to first 20 lines

def analyze_infraction(infraction, chunks, embeddings, confidence_threshold=0.7):
    """Analyze single infraction against spec book"""
    inf_emb = model.encode([infraction])
    cos_scores = util.cos_sim(inf_emb, embeddings)[0]
    
    top_k = 5  # Top matches for better reasoning
    top_idx = cos_scores.argsort(descending=True)[:top_k]
    top_scores = cos_scores[top_idx]
    
    relevant = [(chunks[i], score.item()) for i, score in zip(top_idx, top_scores) if score > 0.5]
    
    # Calculate confidence based on similarity scores
    confidence = sum(score for _, score in relevant) / top_k if relevant else 0.0
    
    # Determine if infraction is repealable
    is_repealable = len(relevant) >= 2 and confidence > confidence_threshold
    
    # Generate reasons
    reasons = []
    for chunk, score in relevant[:3]:  # Top 3 reasons
        if score > 0.5:
            reason = f"Spec match ({score:.0%}): {chunk[:150]}..."
            reasons.append(reason)
    
    return {
        "repealable": is_repealable,
        "confidence": confidence,
        "reasons": reasons,
        "spec_matches": len(relevant)
    }

# UI Layout
st.title("🏗️ NEXA AI Document Analyzer")
st.markdown("**Enterprise QA Audit Tool** - Phase 1 Roadmap Implementation")

# Sidebar for metrics
with st.sidebar:
    st.header("📊 System Metrics")
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Model", "MiniLM-L6-v2", delta="384-dim")
    with col2:
        st.metric("Device", device.upper(), delta="Ready")
    
    st.divider()
    st.subheader("🔧 Settings")
    confidence_threshold = st.slider("Confidence Threshold", 0.0, 1.0, 0.7, 0.05)
    chunk_size = st.slider("Chunk Size", 200, 800, 400, 50)
    
    st.divider()
    st.info(f"**Embeddings Path:** {EMBEDDINGS_PATH}")
    
    # Offline mode indicator
    st.divider()
    if st.checkbox("Offline Mode"):
        st.warning("Offline: Uploads queued for sync")

# Main interface tabs
tab1, tab2, tab3 = st.tabs(["📚 Learn Spec Book", "🔍 Analyze Audit", "📈 Results"])

with tab1:
    st.header("Upload and Learn Spec Book")
    st.markdown("Upload your large spec book PDF (e.g., PG&E sections)")
    
    spec_file = st.file_uploader("Choose Spec Book PDF", type="pdf", key="spec_uploader")
    
    col1, col2 = st.columns([2, 1])
    with col1:
        if st.button("🚀 Learn Spec Book", type="primary", use_container_width=True):
            if spec_file:
                with st.spinner("Processing large spec book... This may take a few minutes"):
                    try:
                        chunks, embeddings = load_or_learn_spec(spec_file)
                        st.success(f"✅ Successfully learned {len(chunks)} chunks from spec book")
                        st.info(f"Embeddings saved to: {EMBEDDINGS_PATH}")
                        
                        # Display sample chunks
                        with st.expander("View Sample Chunks"):
                            for i, chunk in enumerate(chunks[:5]):
                                st.text(f"Chunk {i+1}: {chunk[:200]}...")
                    except Exception as e:
                        st.error(f"Error processing spec: {str(e)}")
            else:
                st.warning("Please upload a spec book first")
    
    with col2:
        if os.path.exists(EMBEDDINGS_PATH):
            st.success("✓ Spec learned")
            if st.button("Clear Cache"):
                os.remove(EMBEDDINGS_PATH)
                st.rerun()
        else:
            st.info("No spec loaded")

with tab2:
    st.header("Analyze QA Audit Document")
    st.markdown("Upload your QA audit document for infraction analysis")
    
    audit_file = st.file_uploader("Choose Audit PDF", type="pdf", key="audit_uploader")
    
    if st.button("🔍 Analyze Infractions", type="primary", use_container_width=True):
        if not os.path.exists(EMBEDDINGS_PATH):
            st.error("❌ Please learn the spec book first (Tab 1)")
        elif not audit_file:
            st.warning("Please upload an audit document")
        else:
            with st.spinner("Cross-referencing audit against spec book..."):
                try:
                    # Extract audit text
                    audit_text = extract_text_from_pdf(audit_file)
                    infractions = extract_go_back_infractions(audit_text)
                    
                    # Load embeddings
                    with open(EMBEDDINGS_PATH, 'rb') as f:
                        chunks, embeddings = pickle.load(f)
                    
                    # Analyze each infraction
                    results = []
                    progress_bar = st.progress(0)
                    
                    for idx, inf in enumerate(infractions):
                        if len(inf.strip()) > 20:  # Skip very short lines
                            analysis = analyze_infraction(inf, chunks, embeddings, confidence_threshold)
                            
                            results.append({
                                "Infraction": inf.strip()[:150] + "..." if len(inf) > 150 else inf.strip(),
                                "Status": "🔴 Repealable" if analysis["repealable"] else "✅ Valid",
                                "Confidence": f"{analysis['confidence']:.1%}",
                                "Spec Matches": analysis["spec_matches"],
                                "Primary Reason": analysis["reasons"][0] if analysis["reasons"] else "No spec match found"
                            })
                        
                        progress_bar.progress((idx + 1) / len(infractions))
                    
                    # Store results in session state
                    st.session_state['analysis_results'] = results
                    st.session_state['analysis_timestamp'] = datetime.now()
                    
                    st.success(f"✅ Analyzed {len(results)} infractions")
                    
                except Exception as e:
                    st.error(f"Analysis error: {str(e)}")

with tab3:
    st.header("Analysis Results")
    
    if 'analysis_results' in st.session_state:
        results = st.session_state['analysis_results']
        timestamp = st.session_state['analysis_timestamp']
        
        # Summary metrics
        col1, col2, col3, col4 = st.columns(4)
        
        total_infractions = len(results)
        repealable = sum(1 for r in results if "🔴" in r["Status"])
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
            filtered_results = [r for r in results if "🔴" in r["Status"]]
        elif status_filter == "Valid":
            filtered_results = [r for r in results if "✅" in r["Status"]]
        
        # Sort results
        if sort_by == "Confidence":
            filtered_results = sorted(filtered_results, key=lambda x: float(x["Confidence"].strip('%')), reverse=True)
        elif sort_by == "Spec Matches":
            filtered_results = sorted(filtered_results, key=lambda x: x["Spec Matches"], reverse=True)
        
        # Display table
        st.dataframe(filtered_results, use_container_width=True)
        
        # Export options
        st.divider()
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("📥 Export to JSON"):
                json_str = json.dumps(filtered_results, indent=2)
                st.download_button(
                    label="Download JSON",
                    data=json_str,
                    file_name=f"audit_analysis_{timestamp.strftime('%Y%m%d_%H%M%S')}.json",
                    mime="application/json"
                )
        
        with col2:
            if st.button("📊 Generate Report"):
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
        st.info("📋 No analysis results yet. Upload and analyze an audit document in Tab 2.")

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
