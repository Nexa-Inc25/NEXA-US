"""
NEXA Document Intelligence - Production Version
Combines spaCy NER, FAISS vector search, xAI analysis, and optimized chunking
"""
import streamlit as st
import spacy
from spacy.matcher import PhraseMatcher
import PyPDF2
from io import BytesIO
import requests
import json
import os
import numpy as np
import faiss
from sentence_transformers import SentenceTransformer
from datetime import datetime
import hashlib
import pickle
from optimized_chunking import ConstructionSpecChunker

# Configuration
XAI_API_KEY = os.environ.get('XAI_API_KEY')
OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')  # Optional fallback
USE_XAI = bool(XAI_API_KEY)

st.set_page_config(
    page_title="NEXA Document Intelligence - Production",
    page_icon="🚧",
    layout="wide"
)

st.title("🚧 AI Document Analyzer for Construction Infractions")
st.markdown("**Production-ready with NER, FAISS, and Dynamic Chunking**")

# Initialize models and tools
@st.cache_resource
def load_spacy_model():
    """Load spaCy model with custom patterns"""
    try:
        nlp = spacy.load("en_core_web_sm")
    except:
        # Download if not available
        os.system("python -m spacy download en_core_web_sm")
        nlp = spacy.load("en_core_web_sm")
    
    # Custom construction-specific patterns
    matcher = PhraseMatcher(nlp.vocab, attr="LOWER")
    
    # Construction-specific infraction patterns
    infraction_patterns = [
        "go-back", "infraction", "violation", "non-compliance", "defect",
        "failed inspection", "not per spec", "incorrect installation",
        "missing component", "improper grounding", "inadequate clearance",
        "voltage drop exceeds", "insulation failure", "corrosion damage"
    ]
    
    patterns = [nlp.make_doc(text) for text in infraction_patterns]
    matcher.add("INFRACTION", patterns)
    
    return nlp, matcher

@st.cache_resource
def load_embeddings_model():
    """Load sentence transformer for embeddings"""
    return SentenceTransformer('all-MiniLM-L6-v2')

@st.cache_resource
def load_chunker():
    """Load optimized chunker for construction docs"""
    return ConstructionSpecChunker()

# Load models
nlp, matcher = load_spacy_model()
embeddings_model = load_embeddings_model()
chunker = load_chunker()

def extract_text_from_pdf(file):
    """Extract text from PDF with error handling"""
    try:
        pdf_reader = PyPDF2.PdfReader(BytesIO(file.read()))
        text = ""
        for i, page in enumerate(pdf_reader.pages):
            page_text = page.extract_text()
            if page_text:
                text += f"\n--- Page {i+1} ---\n{page_text}"
        return text
    except Exception as e:
        st.error(f"Error reading PDF: {e}")
        return ""

def extract_infractions_advanced(audit_text):
    """Advanced infraction extraction using spaCy and patterns"""
    doc = nlp(audit_text[:1000000])  # Limit for performance
    
    # Use matcher for pattern-based extraction
    matches = matcher(doc)
    infractions = []
    seen_contexts = set()
    
    for match_id, start, end in matches:
        # Get surrounding context
        context_start = max(0, start - 20)
        context_end = min(len(doc), end + 20)
        context = doc[context_start:context_end].text
        
        # Avoid duplicates
        context_hash = hashlib.md5(context.encode()).hexdigest()
        if context_hash not in seen_contexts:
            seen_contexts.add(context_hash)
            
            # Extract full sentence containing the infraction
            sent = None
            for s in doc.sents:
                if start >= s.start and end <= s.end:
                    sent = s.text
                    break
            
            # Classify severity based on keywords
            severity = "MEDIUM"
            if any(word in context.lower() for word in ["safety", "hazard", "danger", "critical"]):
                severity = "HIGH"
            elif any(word in context.lower() for word in ["minor", "cosmetic", "recommended"]):
                severity = "LOW"
            
            infractions.append({
                "phrase": doc[start:end].text,
                "context": context,
                "full_sentence": sent or context,
                "severity": severity,
                "position": start
            })
    
    # Sort by position in document
    infractions.sort(key=lambda x: x['position'])
    
    # Also try xAI extraction if available
    if USE_XAI and len(infractions) < 3:  # If few infractions found, use AI
        xai_infractions = extract_infractions_with_xai(audit_text)
        if xai_infractions:
            infractions.extend(xai_infractions)
    
    return infractions

def extract_infractions_with_xai(audit_text):
    """Use xAI for advanced infraction extraction"""
    if not XAI_API_KEY:
        return []
    
    prompt = f"""
    Extract all construction infractions from this audit document.
    Focus on: go-back items, violations, non-compliances, safety issues, installation errors.
    
    Return as JSON array:
    [
      {{
        "phrase": "specific infraction phrase",
        "full_sentence": "complete sentence containing infraction",
        "severity": "HIGH/MEDIUM/LOW",
        "category": "EQUIPMENT/INSTALLATION/SAFETY/MATERIAL/TESTING"
      }}
    ]
    
    Audit excerpt:
    {audit_text[:8000]}
    """
    
    headers = {
        "Authorization": f"Bearer {XAI_API_KEY}",
        "Content-Type": "application/json"
    }
    
    data = {
        "model": "grok-beta",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.1,
        "max_tokens": 1000
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
            # Parse JSON from response
            import re
            json_match = re.search(r'\[.*\]', result, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
        return []
    except:
        return []

def build_faiss_index_optimized(spec_texts):
    """Build FAISS index with optimized chunking"""
    all_chunks = []
    chunk_metadata = []
    
    for i, text in enumerate(spec_texts):
        # Use optimized chunking
        chunks_obj = chunker.chunk_text_smart(text)
        
        for chunk in chunks_obj:
            all_chunks.append(chunk['text'])
            chunk_metadata.append({
                'doc_index': i,
                'chunk_id': chunk.get('id'),
                'section': chunk.get('header', ''),
                'type': chunk.get('type', 'unknown')
            })
    
    if not all_chunks:
        return None, None, None
    
    # Generate embeddings
    embeddings = embeddings_model.encode(all_chunks, show_progress_bar=True)
    embeddings = np.array(embeddings).astype('float32')
    
    # Normalize for cosine similarity
    faiss.normalize_L2(embeddings)
    
    # Create FAISS index
    dimension = embeddings.shape[1]
    index = faiss.IndexFlatIP(dimension)
    index.add(embeddings)
    
    return index, all_chunks, chunk_metadata

def search_specs_for_infraction(infraction, index, chunks, metadata, k=5):
    """Search specifications for relevant context"""
    if not index or not chunks:
        return []
    
    # Generate query embedding
    query_text = infraction.get('full_sentence', infraction.get('context', ''))
    query_embedding = embeddings_model.encode([query_text]).astype('float32')
    faiss.normalize_L2(query_embedding)
    
    # Search
    scores, indices = index.search(query_embedding, min(k, len(chunks)))
    
    results = []
    for score, idx in zip(scores[0], indices[0]):
        if idx < len(chunks):
            results.append({
                'text': chunks[idx],
                'score': float(score),
                'metadata': metadata[idx] if idx < len(metadata) else {}
            })
    
    return results

def analyze_infraction_verdict(infraction, relevant_specs):
    """Analyze if infraction is valid or repealable"""
    
    # Prepare context from specs
    spec_context = "\n\n".join([
        f"[Section: {r['metadata'].get('section', 'Unknown')} | Score: {r['score']:.2%}]\n{r['text'][:500]}"
        for r in relevant_specs[:3]
    ])
    
    if USE_XAI:
        prompt = f"""
        Analyze this construction infraction against specifications:
        
        INFRACTION: {infraction['full_sentence']}
        SEVERITY: {infraction['severity']}
        
        RELEVANT SPECIFICATIONS:
        {spec_context}
        
        Determine:
        1. VERDICT: Is this a valid infraction or repealable?
        2. CONFIDENCE: High/Medium/Low
        3. REASONING: Based on specifications
        4. RECOMMENDATION: Action to take
        
        Format:
        VERDICT: [Valid/Repealable]
        CONFIDENCE: [High/Medium/Low]
        REASONING: [explanation]
        RECOMMENDATION: [action]
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
                return response.json()["choices"][0]["message"]["content"]
        except:
            pass
    
    # Fallback to similarity-based analysis
    if relevant_specs:
        avg_score = np.mean([r['score'] for r in relevant_specs[:3]])
        if avg_score > 0.7:
            return "VERDICT: Valid\nCONFIDENCE: High\nREASONING: Strong match with specifications"
        elif avg_score > 0.4:
            return "VERDICT: Repealable\nCONFIDENCE: Medium\nREASONING: Partial match, context needed"
        else:
            return "VERDICT: Repealable\nCONFIDENCE: Low\nREASONING: Weak match with specifications"
    
    return "VERDICT: Unknown\nCONFIDENCE: Low\nREASONING: No relevant specifications found"

# Main UI
col1, col2 = st.columns([1, 1])

with col1:
    st.header("📚 Upload Spec Book PDFs")
    spec_files = st.file_uploader(
        "Upload specification documents (PG&E, SCE, SDG&E)",
        accept_multiple_files=True,
        type="pdf"
    )

with col2:
    st.header("📋 Upload Audit Document")
    audit_file = st.file_uploader(
        "Upload audit/inspection report",
        type="pdf"
    )

# Process specifications
if spec_files:
    if st.button("📖 Learn Spec Books (Build Index)", type="primary"):
        with st.spinner("Extracting and processing specifications..."):
            spec_texts = []
            for file in spec_files:
                text = extract_text_from_pdf(file)
                if text:
                    spec_texts.append(text)
            
            if spec_texts:
                st.success(f"✅ Extracted text from {len(spec_texts)} documents")
                
                # Build FAISS index
                with st.spinner("Building FAISS index with optimized chunking..."):
                    index, chunks, metadata = build_faiss_index_optimized(spec_texts)
                    
                    if index:
                        st.session_state['faiss_index'] = index
                        st.session_state['chunks'] = chunks
                        st.session_state['metadata'] = metadata
                        
                        # Show statistics
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.metric("Total Chunks", len(chunks))
                        with col2:
                            avg_size = np.mean([len(c) for c in chunks])
                            st.metric("Avg Chunk Size", f"{avg_size:.0f} chars")
                        with col3:
                            st.metric("Documents Indexed", len(spec_texts))
                        
                        st.success("✅ Specifications learned! Ready for analysis.")
                    else:
                        st.error("Failed to build index")

# Process audit
if audit_file and 'faiss_index' in st.session_state:
    if st.button("🔍 Analyze Audit Infractions", type="primary"):
        with st.spinner("Processing audit document..."):
            audit_text = extract_text_from_pdf(audit_file)
            
            if audit_text:
                st.success(f"✅ Audit loaded: {len(audit_text):,} characters")
                
                # Extract infractions
                with st.spinner("Extracting infractions with NER..."):
                    infractions = extract_infractions_advanced(audit_text)
                
                if infractions:
                    st.subheader(f"🚨 Found {len(infractions)} Infractions")
                    
                    # Create tabs
                    tab1, tab2, tab3 = st.tabs(["Detailed Analysis", "Summary", "Export"])
                    
                    with tab1:
                        for i, inf in enumerate(infractions, 1):
                            severity_icon = {
                                'HIGH': '🔴',
                                'MEDIUM': '🟡',
                                'LOW': '🟢'
                            }.get(inf['severity'], '⚪')
                            
                            with st.expander(f"{severity_icon} Infraction {i}: {inf['phrase']}"):
                                # Show infraction details
                                st.write(f"**Full Context:** {inf['full_sentence']}")
                                st.write(f"**Severity:** {inf['severity']}")
                                
                                # Search specifications
                                with st.spinner("Searching specifications..."):
                                    relevant_specs = search_specs_for_infraction(
                                        inf,
                                        st.session_state['faiss_index'],
                                        st.session_state['chunks'],
                                        st.session_state['metadata'],
                                        k=5
                                    )
                                
                                if relevant_specs:
                                    st.markdown("### 📖 Relevant Specifications")
                                    for j, spec in enumerate(relevant_specs[:3], 1):
                                        score = spec['score']
                                        # Color by relevance
                                        if score > 0.8:
                                            color = "🟢"
                                        elif score > 0.6:
                                            color = "🟡"
                                        else:
                                            color = "🔴"
                                        
                                        st.write(f"{color} **Match {j}** (Score: {score:.1%})")
                                        st.write(spec['text'][:300] + "...")
                                
                                # Analyze verdict
                                with st.spinner("Analyzing verdict..."):
                                    verdict = analyze_infraction_verdict(inf, relevant_specs)
                                    
                                    st.markdown("### ⚖️ Analysis")
                                    st.text(verdict)
                    
                    with tab2:
                        # Summary statistics
                        st.markdown("### 📊 Infraction Summary")
                        
                        severity_counts = {'HIGH': 0, 'MEDIUM': 0, 'LOW': 0}
                        for inf in infractions:
                            severity_counts[inf['severity']] = severity_counts.get(inf['severity'], 0) + 1
                        
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.metric("🔴 High Severity", severity_counts['HIGH'])
                        with col2:
                            st.metric("🟡 Medium Severity", severity_counts['MEDIUM'])
                        with col3:
                            st.metric("🟢 Low Severity", severity_counts['LOW'])
                        
                        # Top infraction phrases
                        st.markdown("### Most Common Infraction Types")
                        phrase_counts = {}
                        for inf in infractions:
                            phrase = inf['phrase']
                            phrase_counts[phrase] = phrase_counts.get(phrase, 0) + 1
                        
                        for phrase, count in sorted(phrase_counts.items(), key=lambda x: x[1], reverse=True)[:5]:
                            st.write(f"- **{phrase}**: {count} occurrences")
                    
                    with tab3:
                        # Export results
                        export_data = {
                            'timestamp': datetime.now().isoformat(),
                            'audit_file': audit_file.name,
                            'spec_files': [f.name for f in spec_files],
                            'infractions': infractions,
                            'statistics': {
                                'total': len(infractions),
                                'high_severity': severity_counts['HIGH'],
                                'medium_severity': severity_counts['MEDIUM'],
                                'low_severity': severity_counts['LOW']
                            }
                        }
                        
                        st.download_button(
                            label="📥 Download Analysis Report (JSON)",
                            data=json.dumps(export_data, indent=2),
                            file_name=f"infraction_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                            mime="application/json"
                        )
                else:
                    st.info("No infractions detected in the audit document")
            else:
                st.error("Failed to extract text from audit")
elif not audit_file:
    st.info("👈 Upload specifications and audit document to begin")
elif 'faiss_index' not in st.session_state:
    st.warning("⚠️ Please learn spec books first by clicking the button above")

# Sidebar configuration
st.sidebar.header("⚙️ Configuration")

analysis_method = st.sidebar.radio(
    "Analysis Method",
    ["xAI (Recommended)" if USE_XAI else "Similarity-Based", 
     "Similarity-Based Only"]
)

chunking_config = st.sidebar.expander("Chunking Settings")
with chunking_config:
    chunk_size = st.slider("Chunk Size", 500, 2000, 1200)
    overlap = st.slider("Overlap %", 5, 30, 15)
    chunker.OPTIMAL_CHUNK_SIZE = chunk_size
    chunker.OVERLAP_RATIO = overlap / 100

retrieval_k = st.sidebar.slider("Specs to Retrieve", 3, 10, 5)

# Sidebar info
st.sidebar.markdown("---")
st.sidebar.header("📊 System Status")

if USE_XAI:
    st.sidebar.success("✅ xAI API Connected")
else:
    st.sidebar.warning("⚠️ xAI API not configured")
    st.sidebar.info("Using similarity-based analysis")

if 'faiss_index' in st.session_state:
    st.sidebar.success(f"✅ Index Ready ({len(st.session_state.get('chunks', []))} chunks)")
else:
    st.sidebar.info("⏳ No index built yet")

# Deployment instructions
st.sidebar.markdown("---")
with st.sidebar.expander("🚀 Deployment Guide"):
    st.markdown("""
    ### Deploy on Render.com
    
    1. **Push to GitHub:**
    ```bash
    git add .
    git commit -m "Production app"
    git push origin main
    ```
    
    2. **Create Web Service on Render:**
    - Connect GitHub repo
    - Runtime: Python 3
    - Build: `pip install -r requirements.txt`
    - Start: `streamlit run app_production.py --server.port $PORT`
    
    3. **Environment Variables:**
    ```
    XAI_API_KEY=your_xai_key
    ```
    
    4. **requirements.txt:**
    ```
    streamlit
    spacy
    PyPDF2
    sentence-transformers
    faiss-cpu
    numpy
    requests
    ```
    
    5. **Post-deploy:**
    ```bash
    python -m spacy download en_core_web_sm
    ```
    """)

# Check environment
if not XAI_API_KEY:
    st.warning("💡 Tip: Set XAI_API_KEY environment variable for AI-powered analysis")
