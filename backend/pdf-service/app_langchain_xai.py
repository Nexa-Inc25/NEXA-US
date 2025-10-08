"""
NEXA Document Intelligence - LangChain + xAI Integration
Enhanced version with proper imports and optimizations
"""
import streamlit as st
import spacy
from spacy.matcher import PhraseMatcher
import PyPDF2
import os
import requests
import json
import numpy as np
from datetime import datetime
import hashlib
import faiss

# LangChain imports (updated for compatibility)
try:
    from langchain.embeddings import HuggingFaceEmbeddings
    from langchain.vectorstores import FAISS
    from langchain.text_splitter import RecursiveCharacterTextSplitter
    from langchain.chains import RetrievalQA
    from langchain.llms import OpenAI
except ImportError:
    # Fallback for newer versions
    from langchain_community.embeddings import HuggingFaceEmbeddings
    from langchain_community.vectorstores import FAISS
    from langchain.text_splitter import RecursiveCharacterTextSplitter
    from langchain.chains import RetrievalQA
    from langchain_community.llms import OpenAI

# For direct embeddings if LangChain fails
from sentence_transformers import SentenceTransformer

st.set_page_config(
    page_title="NEXA AI Document Analyzer",
    layout="wide"
)

st.title("AI Document Analyzer for Construction Specs")
st.markdown("**Analyzes PG&E, SCE, SDG&E specifications against audit reports**")

# Initialize session state
if 'vector_store' not in st.session_state:
    st.session_state.vector_store = None
if 'analysis_cache' not in st.session_state:
    st.session_state.analysis_cache = {}

# Load spaCy model with caching
@st.cache_resource
def load_spacy_model():
    """Load spaCy model with construction-specific patterns"""
    try:
        nlp = spacy.load("en_core_web_sm")
    except:
        st.info("Downloading spaCy model...")
        os.system("python -m spacy download en_core_web_sm")
        nlp = spacy.load("en_core_web_sm")
    
    # Extended construction-specific patterns
    matcher = PhraseMatcher(nlp.vocab, attr="LOWER")
    
    infraction_phrases = [
        # General infractions
        "go-back", "infraction", "violation", "non-compliance", "defect", "issue",
        "requirement not met", "installation error", "does not meet", "failed inspection",
        
        # Construction-specific
        "grounding issue", "fusing error", "clearance violation", "improper installation",
        "missing component", "incorrect wiring", "voltage drop exceeds", "insulation failure",
        "corrosion present", "damaged equipment", "improper torque", "inadequate support",
        
        # PG&E specific terms
        "not per spec", "deviation from standard", "safety violation", "code violation",
        "incomplete work", "rework required", "corrective action needed"
    ]
    
    patterns = [nlp.make_doc(text) for text in infraction_phrases]
    matcher.add("INFRACTION", patterns)
    
    return nlp, matcher

# Load models
nlp, matcher = load_spacy_model()

# xAI API Integration
class XAIAnalyzer:
    """Handle xAI API calls with caching and error handling"""
    
    def __init__(self):
        self.api_key = os.environ.get('XAI_API_KEY')
        self.base_url = "https://api.x.ai/v1/chat/completions"
        self.cache = {}
    
    def query(self, prompt, use_cache=True):
        """Query xAI API with caching"""
        if not self.api_key:
            return "xAI API key not configured. Using fallback analysis."
        
        # Check cache
        prompt_hash = hashlib.md5(prompt.encode()).hexdigest()[:10]
        if use_cache and prompt_hash in self.cache:
            return self.cache[prompt_hash]
        
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            data = {
                "model": "grok-beta",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.1,
                "max_tokens": 500
            }
            
            response = requests.post(self.base_url, headers=headers, json=data, timeout=30)
            
            if response.status_code == 200:
                result = response.json()["choices"][0]["message"]["content"]
                self.cache[prompt_hash] = result
                return result
            else:
                return f"API Error: {response.status_code}"
                
        except Exception as e:
            return f"Error: {str(e)}"

xai = XAIAnalyzer()

def extract_text_from_pdf(file):
    """Extract text from PDF with error handling"""
    try:
        file.seek(0)  # Reset file pointer
        pdf_reader = PyPDF2.PdfReader(file)
        text = ""
        for i, page in enumerate(pdf_reader.pages):
            page_text = page.extract_text()
            if page_text:
                text += f"\n--- Page {i+1} ---\n{page_text}"
        return text
    except Exception as e:
        st.error(f"Error reading PDF: {e}")
        return ""

def chunk_text_optimized(text, doc_type="spec"):
    """Optimized chunking based on document type and structure"""
    doc_length = len(text)
    
    # Adaptive chunk sizing
    if doc_type == "spec":
        if doc_length < 10000:
            chunk_size = 800
            overlap = 100
        elif doc_length < 50000:
            chunk_size = 1500
            overlap = 200
        else:
            chunk_size = 2000
            overlap = 300
    else:  # audit
        chunk_size = 600
        overlap = 100
    
    # Use RecursiveCharacterTextSplitter with construction-aware separators
    separators = [
        "\n\n\n",  # Major sections
        "\n\n",    # Paragraphs
        "\n",      # Lines
        ".",       # Sentences
        " "        # Words
    ]
    
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=overlap,
        separators=separators,
        length_function=len
    )
    
    chunks = text_splitter.split_text(text)
    return chunks

def extract_infractions_advanced(audit_text):
    """Extract infractions with enhanced context"""
    doc = nlp(audit_text[:500000])  # Limit for performance
    matches = matcher(doc)
    
    infractions = []
    seen = set()
    
    for match_id, start, end in matches:
        # Get full sentence containing the match
        sent = None
        for s in doc.sents:
            if start >= s.start and end <= s.end:
                sent = s
                break
        
        if sent:
            context = sent.text
            # Avoid duplicates
            if context not in seen:
                seen.add(context)
                
                # Determine severity
                severity = "MEDIUM"
                context_lower = context.lower()
                if any(word in context_lower for word in ["safety", "hazard", "critical", "danger"]):
                    severity = "HIGH"
                elif any(word in context_lower for word in ["minor", "cosmetic", "suggested"]):
                    severity = "LOW"
                
                infractions.append({
                    "infraction": doc[start:end].text,
                    "context": context,
                    "severity": severity,
                    "position": start
                })
    
    return infractions

def build_faiss_index_optimized(spec_texts):
    """Build optimized FAISS index - renamed function"""
    return build_faiss_index(spec_texts)

@st.cache_resource
def build_faiss_index(spec_texts):
    """Build FAISS index with progress tracking"""
    all_chunks = []
    chunk_metadata = []
    
    progress_bar = st.progress(0)
    for i, text in enumerate(spec_texts):
        progress_bar.progress((i + 1) / len(spec_texts))
        chunks = chunk_text_optimized(text, doc_type="spec")
        
        for j, chunk in enumerate(chunks):
            all_chunks.append(chunk)
            chunk_metadata.append({
                "doc_index": i,
                "chunk_index": j,
                "preview": chunk[:100]
            })
    
    progress_bar.empty()
    
    # Create embeddings
    with st.spinner("Creating embeddings..."):
        embeddings = HuggingFaceEmbeddings(
            model_name="sentence-transformers/all-MiniLM-L6-v2",
            model_kwargs={'device': 'cpu'}
        )
        
        # Build FAISS index
        vector_store = FAISS.from_texts(all_chunks, embeddings, metadatas=chunk_metadata)
    
    return vector_store, chunk_metadata

def analyze_infraction_with_specs(infraction, vector_store, use_xai=True):
    """Analyze infraction against specifications"""
    
    # Retrieve relevant specs
    retriever = vector_store.as_retriever(
        search_type="similarity",
        search_kwargs={"k": 5}
    )
    
    # Get relevant documents
    relevant_docs = retriever.get_relevant_documents(infraction['context'])
    
    # Prepare context
    spec_context = "\n\n".join([doc.page_content[:500] for doc in relevant_docs[:3]])
    
    # Analysis prompt
    analysis_prompt = f"""
    Analyze this construction audit infraction against specifications:
    
    INFRACTION: {infraction['context']}
    SEVERITY: {infraction['severity']}
    
    RELEVANT SPECIFICATIONS:
    {spec_context}
    
    Determine:
    1. VERDICT: Is this a valid infraction or can it be appealed?
    2. CONFIDENCE: High/Medium/Low
    3. SPECIFICATION REFERENCE: Quote the exact spec that applies
    4. REASONING: Detailed explanation
    5. RECOMMENDATION: Required action
    
    Format response as:
    VERDICT: [Valid/Appealable]
    CONFIDENCE: [High/Medium/Low]
    SPEC_REF: [exact specification quote]
    REASONING: [explanation]
    RECOMMENDATION: [action]
    """
    
    if use_xai and xai.api_key:
        return xai.query(analysis_prompt)
    else:
        # Fallback to similarity-based analysis
        if relevant_docs:
            avg_score = np.mean([doc.metadata.get('score', 0.5) for doc in relevant_docs[:3]])
            if avg_score > 0.7:
                return "VERDICT: Valid\nCONFIDENCE: High\nREASONING: Strong match with specifications"
            elif avg_score > 0.4:
                return "VERDICT: Appealable\nCONFIDENCE: Medium\nREASONING: Partial match, review needed"
            else:
                return "VERDICT: Appealable\nCONFIDENCE: Low\nREASONING: Weak correlation with specs"
        return "VERDICT: Unknown\nCONFIDENCE: Low\nREASONING: No specifications found"

# Main UI
col1, col2 = st.columns([1, 1])

with col1:
    st.header("Upload Spec Book PDFs")
    spec_files = st.file_uploader(
        "Upload specification documents (PG&E, SCE, SDG&E)",
        accept_multiple_files=True,
        type="pdf",
        help="Upload standards like UG-1, transformer specs, etc."
    )

with col2:
    st.header("Upload Audit Documents")
    audit_files = st.file_uploader(
        "Upload audit/inspection reports",
        accept_multiple_files=True,
        type="pdf",
        help="Upload QA audits with infractions"
    )

# Process specifications
if spec_files:
    if st.button("Learn Spec Books (Build Index)", type="primary"):
        spec_texts = []
        
        with st.spinner("Extracting text from specifications..."):
            for file in spec_files:
                text = extract_text_from_pdf(file)
                if text:
                    spec_texts.append(text)
        
        if spec_texts:
            st.success(f"Extracted {len(spec_texts)} specification documents")
            
            # Build FAISS index
            vector_store, metadata = build_faiss_index_optimized(spec_texts)
            st.session_state.vector_store = vector_store
            st.session_state.metadata = metadata
            
            # Show statistics
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Documents Indexed", len(spec_texts))
            with col2:
                st.metric("Total Chunks", len(metadata))
            with col3:
                avg_chunk_size = sum(len(m['preview']) for m in metadata) / len(metadata) * 10
                st.metric("Avg Chunk Size", f"{avg_chunk_size:.0f} chars")
            
            st.success("Specifications indexed! Ready for analysis.")

# Process audits
if audit_files and st.session_state.vector_store:
    if st.button("Analyze Audit Infractions", type="primary"):
        all_infractions = []
        
        for audit_file in audit_files:
            with st.spinner(f"Processing {audit_file.name}..."):
                audit_text = extract_text_from_pdf(audit_file)
                
                if audit_text:
                    # Extract infractions
                    infractions = extract_infractions_advanced(audit_text)
                    
                    for inf in infractions:
                        inf['source_file'] = audit_file.name
                    
                    all_infractions.extend(infractions)
        
        if all_infractions:
            st.subheader(f"Found {len(all_infractions)} Total Infractions")
            
            # Analysis options
            use_xai = st.checkbox("Use xAI for enhanced analysis", value=bool(xai.api_key))
            
            # Create tabs for organization
            tab1, tab2, tab3 = st.tabs(["Detailed Analysis", "Summary", "Export"])
            
            with tab1:
                for i, inf in enumerate(all_infractions, 1):
                    severity_icon = {
                        'HIGH': '[HIGH]',
                        'MEDIUM': '[MEDIUM]', 
                        'LOW': '[LOW]'
                    }.get(inf['severity'], '[UNKNOWN]')
                    
                    with st.expander(f"{severity_icon} Infraction {i}: {inf['infraction']} ({inf['source_file']})"):
                        st.write(f"**Context:** {inf['context']}")
                        st.write(f"**Severity:** {inf['severity']}")
                        
                        # Analyze with specs
                        with st.spinner("Analyzing against specifications..."):
                            analysis = analyze_infraction_with_specs(
                                inf,
                                st.session_state.vector_store,
                                use_xai=use_xai
                            )
                        
                        st.markdown("### Analysis Result")
                        st.text(analysis)
                        
                        # Parse verdict for visual feedback
                        if "VERDICT: Valid" in analysis:
                            st.error("Valid Infraction - Requires Correction")
                        elif "VERDICT: Appealable" in analysis:
                            st.success("Potentially Appealable - Review Specs")
                        else:
                            st.warning("Requires Manual Review")
            
            with tab2:
                # Summary statistics
                st.markdown("### Infraction Summary")
                
                # By severity
                severity_counts = {'HIGH': 0, 'MEDIUM': 0, 'LOW': 0}
                for inf in all_infractions:
                    severity_counts[inf['severity']] += 1
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("High", severity_counts['HIGH'])
                with col2:
                    st.metric("Medium", severity_counts['MEDIUM'])
                with col3:
                    st.metric("Low", severity_counts['LOW'])
                
                # By source file
                st.markdown("### By Audit File")
                file_counts = {}
                for inf in all_infractions:
                    file_counts[inf['source_file']] = file_counts.get(inf['source_file'], 0) + 1
                
                for file, count in file_counts.items():
                    st.write(f"- **{file}**: {count} infractions")
            
            with tab3:
                # Export functionality
                export_data = {
                    'timestamp': datetime.now().isoformat(),
                    'spec_files': [f.name for f in spec_files],
                    'audit_files': [f.name for f in audit_files],
                    'infractions': all_infractions,
                    'total_count': len(all_infractions),
                    'severity_breakdown': severity_counts
                }
                
                st.download_button(
                    label="Download Analysis Report (JSON)",
                    data=json.dumps(export_data, indent=2, default=str),
                    file_name=f"infraction_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                    mime="application/json"
                )
        else:
            st.info("No infractions detected in the audit documents")

elif not st.session_state.vector_store:
    st.warning("Please upload and index specification documents first")

# Sidebar configuration
st.sidebar.header("Configuration")

# API Status
st.sidebar.markdown("### API Status")
if xai.api_key:
    st.sidebar.success("xAI API Connected")
else:
    st.sidebar.warning("xAI API Not Configured")
    st.sidebar.info("Set XAI_API_KEY environment variable")

openai_key = os.environ.get('OPENAI_API_KEY')
if openai_key:
    st.sidebar.success("OpenAI API Connected")
else:
    st.sidebar.info("OpenAI API not configured (optional)")

# Index Status
if st.session_state.vector_store:
    st.sidebar.success(f"Index Ready")
else:
    st.sidebar.info("No index built yet")

# Deployment Guide
with st.sidebar.expander("Deployment Guide"):
    st.markdown("""
    ### Deploy on Render.com
    
    1. **Create requirements.txt:**
    ```
    streamlit
    spacy
    PyPDF2
    langchain
    langchain-community
    faiss-cpu
    sentence-transformers
    openai
    requests
    numpy
    ```
    
    2. **Push to GitHub:**
    ```bash
    git add .
    git commit -m "NEXA Document Analyzer"
    git push
    ```
    
    3. **On Render.com:**
    - New Web Service
    - Connect GitHub repo
    - Build: `pip install -r requirements.txt && python -m spacy download en_core_web_sm`
    - Start: `streamlit run app_langchain_xai.py --server.port $PORT`
    
    4. **Environment Variables:**
    ```
    XAI_API_KEY=your_xai_key
    OPENAI_API_KEY=your_openai_key (optional)
    ```
    """)

# Performance Tips
with st.sidebar.expander("Performance Tips"):
    st.markdown("""
    - **Chunk Size**: Larger for specs (1500-2000), smaller for audits (500-800)
    - **Retrieval K**: 5-7 for best balance
    - **Cache**: Results are cached to reduce API calls
    - **Batch**: Upload multiple files at once
    """)

# Footer
st.markdown("---")
st.markdown("**NEXA Document Intelligence** | Powered by FAISS + xAI | © 2024")
